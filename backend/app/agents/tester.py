from collections.abc import Callable

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.tools.bash import BashTool
from app.tools.filesystem import FileSystemTool

TEST_FILENAME = "test_solution.py"

_DEMO_TEST_FILE = """from solution import solution


def test_solution_adds_numbers():
    assert solution(2, 3) == 5
"""


def _placeholder_check(code: str) -> bool:
    return bool(code) and "TODO" not in code


class TesterAgent(BaseAgent):
    name = "tester"
    __test__ = False

    def __init__(self, check_fn: Callable[[str], bool] | None = None) -> None:
        self._check_fn = check_fn

    def run(self, context: AgentContext) -> AgentResult:
        code = context.memory.get("code", "")

        if self._check_fn is not None:
            passed = self._check_fn(code)
            context.memory["test_passed"] = passed
            summary = "All checks passed." if passed else "Checks failed: code did not meet requirements."
            return AgentResult(output=summary, success=passed, metadata={"passed": passed})

        workspace_dir = context.memory.get("workspace_dir")
        if not workspace_dir:
            passed = _placeholder_check(code)
            context.memory["test_passed"] = passed
            summary = "All checks passed." if passed else "Checks failed: code did not meet requirements."
            return AgentResult(output=summary, success=passed, metadata={"passed": passed})

        fs = FileSystemTool(root=workspace_dir)
        fs.run(action="write", path="solution.py", content=code)
        fs.run(action="write", path=TEST_FILENAME, content=_DEMO_TEST_FILE)

        bash = BashTool(cwd=workspace_dir)
        result = bash.run(f"python -m pytest {TEST_FILENAME} -q")

        context.memory["test_passed"] = result.success
        summary = result.output.strip() or ("All checks passed." if result.success else "Checks failed.")

        return AgentResult(
            output=summary,
            success=result.success,
            metadata={"passed": result.success, "pytest_output": result.output},
        )