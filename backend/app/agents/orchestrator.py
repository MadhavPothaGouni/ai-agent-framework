from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentContext
from app.agents.coder import CoderAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.core.config import get_settings
import uuid
from pathlib import Path

@dataclass
class WorkflowStep:
    agent: str
    output: str
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    steps: list[WorkflowStep]
    final_decision: str
    attempts: int


class DevWorkflow:
    def __init__(self, max_attempts: int = 2, tester: TesterAgent | None = None) -> None:
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.tester = tester or TesterAgent()
        self.reviewer = ReviewerAgent()
        self.max_attempts = max_attempts

    def run(self, task: str, history: list[dict[str, str]] | None = None) -> WorkflowResult:
        context = AgentContext(task=task, history=history or [{"role": "user", "content": task}])
        run_id = uuid.uuid4().hex
        workspace_dir = Path(get_settings().workspace_root) / run_id
        context.memory["workspace_dir"] = str(workspace_dir)
        steps: list[WorkflowStep] = []

        plan_result = self.planner.run(context)
        context.memory["plan"] = plan_result.output
        steps.append(WorkflowStep("planner", plan_result.output, plan_result.success, plan_result.metadata))

        attempt = 0
        test_result = None
        while attempt < self.max_attempts:
            attempt += 1

            code_result = self.coder.run(context)
            steps.append(WorkflowStep("coder", code_result.output, code_result.success, code_result.metadata))

            test_result = self.tester.run(context)
            steps.append(WorkflowStep("tester", test_result.output, test_result.success, test_result.metadata))

            if test_result.success:
                break

            context.memory["previous_failure"] = test_result.output

        review_result = self.reviewer.run(context)
        steps.append(WorkflowStep("reviewer", review_result.output, review_result.success, review_result.metadata))

        return WorkflowResult(
            steps=steps,
            final_decision=context.memory.get("review_decision", "unknown"),
            attempts=attempt,
        )