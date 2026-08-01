
import asyncio
import queue
import threading

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents import run_store
from app.agents.orchestrator import DevWorkflow, WorkflowStep
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User

router = APIRouter()
logger = get_logger("workflow_ws")

# Distinct from HTTP status codes — the WebSocket close code range for
# application-defined codes starts at 4000. Not load-bearing for the
# frontend today, just documents *why* the connection was closed.
_CLOSE_UNAUTHORIZED = 4401
_CLOSE_BAD_REQUEST = 4400

_STEP_SENTINEL = object()


def _authenticate(token: str | None, db: Session) -> User | None:
    if not token:
        return None
    try:
        email = decode_access_token(token)
    except Exception:  # noqa: BLE001 — any decode failure means "not authenticated"
        return None
    return db.query(User).filter(User.email == email).first()


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

        loop = asyncio.get_running_loop()
        step_queue: "queue.Queue" = queue.Queue()
        result_holder: dict = {}

        def on_step(step: WorkflowStep) -> None:
            step_queue.put(step)

        def run_workflow() -> None:
            try:
                result_holder["result"] = DevWorkflow().run(task, on_step=on_step)
            except Exception as exc:  # noqa: BLE001 — surface it to the client instead of hanging
                result_holder["error"] = str(exc)
            finally:
                step_queue.put(_STEP_SENTINEL)

        worker = threading.Thread(target=run_workflow, daemon=True)
        worker.start()

        # Drain the queue and forward each step to the client the moment
        # it's available, instead of waiting for the whole workflow.
        while True:
            item = await loop.run_in_executor(None, step_queue.get)
            if item is _STEP_SENTINEL:
                break
            await websocket.send_json(
                {
                    "type": "step",
                    "agent": item.agent,
                    "output": item.output,
                    "success": item.success,
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
            }
        )
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("workflow_ws_client_disconnected")
    finally:
        db.close()