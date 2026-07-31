from collections.abc import Callable

from app.agents.base import AgentContext, AgentResult, BaseAgent


def _default_check(code: str) -> bool:
    return bool(code) and "TODO" not in code


class TesterAgent(BaseAgent):
    name = "tester"
    __test__ = False  # tell pytest this isn't a test class despite the name

    def __init__(self, check_fn: Callable[[str], bool] | None = None) -> None:
        self._check_fn = check_fn or _default_check

    def run(self, context: AgentContext) -> AgentResult:
        code = context.memory.get("code", "")
        passed = self._check_fn(code)

        summary = "All checks passed." if passed else "Checks failed: code did not meet requirements."
        context.memory["test_passed"] = passed

        return AgentResult(output=summary, success=passed, metadata={"passed": passed})