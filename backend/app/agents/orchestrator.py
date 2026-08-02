import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.coder import CoderAgent
from app.agents.debugger import DebuggerAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.security_auditor import SecurityAuditorAgent
from app.agents.tester import TesterAgent
from app.core.config import get_settings
from app.core.cost_tracker import UsageEvent, set_current_agent, start_ledger
from app.core.logging import get_logger

logger = get_logger("orchestrator")


@dataclass
class WorkflowStep:
    agent: str
    output: str
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    run_id: str
    steps: list[WorkflowStep]
    final_decision: str
    attempts: int
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    usage_events: list[UsageEvent] = field(default_factory=list)


def _run_agent(agent: BaseAgent, context: AgentContext, run_id: str) -> AgentResult:
    """Runs an agent and logs a structured line — one per agent step, every run."""
    set_current_agent(agent.name)
    start = time.perf_counter()
    result = agent.run(context)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "agent_step",
        extra={
            "run_id": run_id,
            "agent": agent.name,
            "success": result.success,
            "duration_ms": duration_ms,
        },
    )
    return result


class DevWorkflow:
    def __init__(
        self,
        max_attempts: int = 2,
        tester: TesterAgent | None = None,
        debugger: DebuggerAgent | None = None,
        security_auditor: SecurityAuditorAgent | None = None,
    ) -> None:
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.tester = tester or TesterAgent()
        self.debugger = debugger or DebuggerAgent()
        self.security_auditor = security_auditor or SecurityAuditorAgent()
        self.reviewer = ReviewerAgent()
        self.max_attempts = max_attempts

    def run(
        self,
        task: str,
        history: list[dict[str, str]] | None = None,
        on_step: Callable[[WorkflowStep], None] | None = None,
        require_approval: bool = False,
        on_approval_required: Callable[[str, WorkflowStep], bool] | None = None,
        check_budget_exceeded: Callable[[float], bool] | None = None,
    ) -> WorkflowResult:
        context = AgentContext(task=task, history=history or [{"role": "user", "content": task}])

        run_id = uuid.uuid4().hex
        workspace_dir = Path(get_settings().workspace_root) / run_id
        context.memory["workspace_dir"] = str(workspace_dir)

        ledger = start_ledger()

        logger.info("workflow_started", extra={"run_id": run_id, "task": task, "require_approval": require_approval})
        steps: list[WorkflowStep] = []

        def record(agent_name: str, result: AgentResult) -> WorkflowStep:
            step = WorkflowStep(agent_name, result.output, result.success, result.metadata)
            steps.append(step)
            if on_step is not None:
                on_step(step)
            return step

        if check_budget_exceeded is not None and check_budget_exceeded(0.0):
            record(
                "budget_guard",
                AgentResult(
                    output="Monthly budget cap already reached — this workflow was not started.",
                    success=False,
                    metadata={},
                ),
            )
            logger.info("workflow_blocked_by_budget", extra={"run_id": run_id})
            return WorkflowResult(
                run_id=run_id,
                steps=steps,
                final_decision="budget_exceeded",
                attempts=0,
                total_cost_usd=0.0,
                total_tokens=0,
            )

        plan_result = _run_agent(self.planner, context, run_id)
        context.memory["plan"] = plan_result.output
        record("planner", plan_result)

        attempt = 0
        test_result = None
        human_rejected = False

        while attempt < self.max_attempts:
            attempt += 1

            code_result = _run_agent(self.coder, context, run_id)
            coder_step = record("coder", code_result)

            if require_approval and on_approval_required is not None:
                approval_id = uuid.uuid4().hex
                start = time.perf_counter()
                approved = on_approval_required(approval_id, coder_step)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)

                logger.info(
                    "human_approval_decided",
                    extra={
                        "run_id": run_id,
                        "approval_id": approval_id,
                        "approved": approved,
                        "duration_ms": duration_ms,
                    },
                )

                if not approved:
                    human_rejected = True
                    context.memory["test_passed"] = False
                    record(
                        "human_review",
                        AgentResult(
                            output="Rejected by human reviewer before execution — the Tester never ran this code.",
                            success=False,
                            metadata={"approval_id": approval_id},
                        ),
                    )
                    break

                record(
                    "human_review",
                    AgentResult(
                        output="Approved by human reviewer — proceeding to run the Tester.",
                        success=True,
                        metadata={"approval_id": approval_id},
                    ),
                )

            test_result = _run_agent(self.tester, context, run_id)
            record("tester", test_result)

            if test_result.success:
                break

            context.memory["last_test_output"] = test_result.output
            debug_result = _run_agent(self.debugger, context, run_id)
            record("debugger", debug_result)
            context.memory["previous_failure"] = context.memory.get("debug_diagnosis", test_result.output)

            if check_budget_exceeded is not None and check_budget_exceeded(ledger.total_cost_usd):
                record(
                    "budget_guard",
                    AgentResult(
                        output=(
                            f"Monthly budget cap reached (~${ledger.total_cost_usd:.4f} spent so far "
                            "this run) — stopping retries early instead of attempting another fix."
                        ),
                        success=False,
                        metadata={"cost_usd_so_far": ledger.total_cost_usd},
                    ),
                )
                logger.info("workflow_retries_stopped_by_budget", extra={"run_id": run_id, "attempt": attempt})
                break

        if not human_rejected:
            security_result = _run_agent(self.security_auditor, context, run_id)
            record("security_auditor", security_result)
        else:
            # Nothing ran, so there's nothing to statically analyze — don't
            # claim a security pass on code that was never approved to execute.
            context.memory["security_passed"] = True

        review_result = _run_agent(self.reviewer, context, run_id)
        record("reviewer", review_result)

        final_decision = context.memory.get("review_decision", "unknown")
        logger.info(
            "workflow_finished",
            extra={
                "run_id": run_id,
                "final_decision": final_decision,
                "attempts": attempt,
                "total_cost_usd": ledger.total_cost_usd,
                "total_tokens": ledger.total_tokens,
            },
        )

        return WorkflowResult(
            run_id=run_id,
            steps=steps,
            final_decision=final_decision,
            attempts=attempt,
            total_cost_usd=ledger.total_cost_usd,
            total_tokens=ledger.total_tokens,
            usage_events=ledger.events,
        )