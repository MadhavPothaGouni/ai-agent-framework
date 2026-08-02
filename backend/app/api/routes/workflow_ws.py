
import asyncio
import queue
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents import run_store
from app.agents.approval_registry import get_approval_registry
from app.agents.budget import make_budget_checker
from app.agents.orchestrator import DevWorkflow, WorkflowStep
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.approval import ApprovalRequest
from app.models.user import User

router = APIRouter()
logger = get_logger("workflow_ws")

# Distinct from HTTP status codes — the WebSocket close code range for
# application-defined codes starts at 4000. Not load-bearing for the
# frontend today, just documents *why* the connection was closed.
_CLOSE_UNAUTHORIZED = 4401
_CLOSE_BAD_REQUEST = 4400

# How long a Coder's code can sit waiting for a human before the workflow
# gives up and treats it as a rejection — long enough for a real person to
# actually read the diff, short enough that a worker thread can't leak
# forever if everyone just closes the tab.
_APPROVAL_TIMEOUT_SECONDS = 600.0

_STEP_SENTINEL = object()


def _authenticate(token: str | None, db: Session) -> User | None:
    if not token:
        return None
    try:
        email = decode_access_token(token)
    except Exception:  # noqa: BLE001 — any decode failure means "not authenticated"
        return None
    return db.query(User).filter(User.email == email).first()


async def _await_approval_decision(
    websocket: WebSocket, registry, expected_approval_id: str, poll_interval: float = 0.2
) -> bool | None:
  
    disconnected = False

    while registry.exists(expected_approval_id):
        if disconnected:
            # Nothing more we can do but wait for the ticket to disappear
            # (resolved via REST, or the registry's own timeout).
            await asyncio.sleep(poll_interval)
            continue

        try:
            client_msg = await asyncio.wait_for(websocket.receive_json(), timeout=poll_interval)
        except asyncio.TimeoutError:
            continue
        except WebSocketDisconnect:
            disconnected = True
            continue
        except Exception:  # noqa: BLE001 — malformed frame; ignore and keep waiting
            continue

        if not isinstance(client_msg, dict) or client_msg.get("type") != "approval_decision":
            continue
        if str(client_msg.get("approval_id", "")) != expected_approval_id:
            continue

        approved = bool(client_msg.get("approved", False))
        if registry.resolve(expected_approval_id, approved):
            return approved
        return None  # someone else (REST) already resolved it in the meantime

    return None


@router.websocket("/ws/run")
async def workflow_run_ws(websocket: WebSocket, token: str | None = None) -> None:
    db = SessionLocal()
    try:
        user = _authenticate(token, db)
        if user is None:
            await websocket.close(code=_CLOSE_UNAUTHORIZED)
            return

        await websocket.accept()

        try:
            init = await websocket.receive_json()
        except Exception:
            await websocket.close(code=_CLOSE_BAD_REQUEST)
            return

        task = str((init or {}).get("task", "")).strip()
        if not task:
            await websocket.send_json({"type": "error", "message": "Missing 'task' in first message"})
            await websocket.close(code=_CLOSE_BAD_REQUEST)
            return

        require_approval = bool((init or {}).get("require_approval", False))

        loop = asyncio.get_running_loop()
        step_queue: "queue.Queue" = queue.Queue()
        result_holder: dict = {}
        registry = get_approval_registry()
        run_id_holder: dict[str, str] = {}

        def on_step(step: WorkflowStep) -> None:
            step_queue.put(("step", step))

        def on_approval_required(approval_id: str, step: WorkflowStep) -> bool:
            registry.create(approval_id)
            step_queue.put(("approval_required", approval_id, step))
            decision = registry.wait(approval_id, timeout=_APPROVAL_TIMEOUT_SECONDS)
            registry.discard(approval_id)
            return bool(decision)

        budget_checker = make_budget_checker(db, user.id)

        def run_workflow() -> None:
            try:
                result = DevWorkflow().run(
                    task,
                    on_step=on_step,
                    require_approval=require_approval,
                    on_approval_required=on_approval_required if require_approval else None,
                    check_budget_exceeded=budget_checker,
                )
                run_id_holder["run_id"] = result.run_id
                result_holder["result"] = result
            except Exception as exc:  # noqa: BLE001 — surface it to the client instead of hanging
                result_holder["error"] = str(exc)
            finally:
                step_queue.put(("done",))

        worker = threading.Thread(target=run_workflow, daemon=True)
        worker.start()

        # Drain the queue and forward each step to the client the moment
        # it's available, instead of waiting for the whole workflow.
        while True:
            item = await loop.run_in_executor(None, step_queue.get)
            kind = item[0]

            if kind == "done":
                break

            if kind == "approval_required":
                _, approval_id, step = item
                db.add(
                    ApprovalRequest(
                        approval_id=approval_id,
                        run_id=run_id_holder.get("run_id", ""),
                        user_id=user.id,
                        code=step.output,
                        status="pending",
                    )
                )
                db.commit()

                await websocket.send_json(
                    {
                        "type": "approval_required",
                        "approval_id": approval_id,
                        "agent": step.agent,
                        "output": step.output,
                    }
                )

                # Block right here, waiting only for this one decision —
                # the worker thread is doing the same thing on its side via
                # ApprovalRegistry.wait(), so both sides unblock together
                # the moment resolve() is called from anywhere (this socket
                # or the REST fallback).
                decision = await _await_approval_decision(websocket, registry, approval_id)

                if decision is not None:
                    # This socket was the one that actually resolved it —
                    # the REST endpoint (workflow_approvals.py) updates the
                    # DB row itself when it's the one resolving, so only do
                    # it here for the WS-resolved path to avoid a double
                    # update racing against it.
                    record = (
                        db.query(ApprovalRequest)
                        .filter(ApprovalRequest.approval_id == approval_id)
                        .first()
                    )
                    if record is not None:
                        record.status = "approved" if decision else "rejected"
                        record.resolved_at = datetime.now(timezone.utc)
                        db.commit()
                continue

            step = item[1]
            await websocket.send_json(
                {
                    "type": "step",
                    "agent": step.agent,
                    "output": step.output,
                    "success": step.success,
                }
            )

        await loop.run_in_executor(None, worker.join)

        if "error" in result_holder:
            await websocket.send_json({"type": "error", "message": result_holder["error"]})
            await websocket.close(code=1011)  # 1011 = internal error
            return

        result = result_holder["result"]
        run_store.save_run(db, user.id, task, result)

        await websocket.send_json(
            {
                "type": "done",
                "run_id": result.run_id,
                "final_decision": result.final_decision,
                "attempts": result.attempts,
                "total_cost_usd": result.total_cost_usd,
                "total_tokens": result.total_tokens,
            }
        )
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("workflow_ws_client_disconnected")
    finally:
        db.close()