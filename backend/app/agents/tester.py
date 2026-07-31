from collections.abc import Callable

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.code_extraction import extract_code_block
from app.core.providers import get_provider
from app.core.providers.base import LLMProvider
from app.tools.bash import BashTool
from app.tools.filesystem import FileSystemTool

TEST_FILENAME = "test_solution.py"

_DEMO_TEST_FILE = """from solution import solution


def test_solution_adds_numbers():
    assert solution(2, 3) == 5
"""


def _placeholder_check(code: str) -> bool:
    return bool(code) and "TODO" not in code


def _build_test_file(provider: LLMProvider, task: str, code: str) -> str:
    prompt = (
        "You are a QA agent. Below is a Python implementation written for this task:\n"
        f"Task: {task}\n\n"
        f"Implementation (saved as solution.py):\n{code}\n\n"
        "Write a pytest test file that imports from `solution` and tests the "
        "actual function(s)/class(es) defined above with at least two meaningful "
        "test cases. Return ONLY the complete Python source code for the test "
        "file — no markdown formatting, no explanations, just the code."
    )
    raw = provider.complete([{"role": "user", "content": prompt}])
    return extract_code_block(raw)


class TesterAgent(BaseAgent):
    name = "tester"
    __test__ = False

    def __init__(
        self,
        check_fn: Callable[[str], bool] | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self._check_fn = check_fn
        self._provider = provider

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

        provider = self._provider or get_provider()
        test_file_content = (
            _DEMO_TEST_FILE if provider.name == "mock" else _build_test_file(provider, context.task, code)
        )

        fs = FileSystemTool(root=workspace_dir)
        fs.run(action="write", path="solution.py", content=code)
        fs.run(action="write", path=TEST_FILENAME, content=test_file_content)

        bash = BashTool(cwd=workspace_dir)
        result = bash.run(f"python -m pytest {TEST_FILENAME} -q")

        context.memory["test_passed"] = result.success
        summary = result.output.strip() or ("All checks passed." if result.success else "Checks failed.")

        return AgentResult(
            output=summary,
            success=result.success,
            metadata={"passed": result.success, "pytest_output": result.output},
        )