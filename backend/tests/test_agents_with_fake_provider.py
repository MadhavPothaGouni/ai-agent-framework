import tempfile

from app.agents.base import AgentContext
from app.agents.coder import CoderAgent
from app.agents.tester import TesterAgent
from app.core.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    name = "fake-real"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, messages: list[dict[str, str]]) -> str:
        return self._responses.pop(0)


FENCED_CODE = (
    "Sure, here's the implementation:\n\n"
    "```python\n"
    "def add(a: int, b: int) -> int:\n"
    "    return a + b\n"
    "```\n"
)

FENCED_TEST = (
    "```python\n"
    "from solution import add\n\n\n"
    "def test_add_positive_numbers():\n"
    "    assert add(2, 3) == 5\n\n\n"
    "def test_add_negative_numbers():\n"
    "    assert add(-1, -1) == -2\n"
    "```\n"
)


def test_coder_agent_strips_markdown_fences_from_real_provider_output():
    provider = FakeProvider([FENCED_CODE])
    context = AgentContext(task="write an add function", history=[])

    result = CoderAgent(provider=provider).run(context)

    assert "```" not in result.output
    assert result.output.strip() == "def add(a: int, b: int) -> int:\n    return a + b"
    assert context.memory["code"] == result.output


def test_tester_agent_generates_and_runs_real_tests_for_non_mock_provider():
    with tempfile.TemporaryDirectory() as workspace_dir:
        context = AgentContext(task="write an add function", history=[])
        context.memory["workspace_dir"] = workspace_dir

        coder_provider = FakeProvider([FENCED_CODE])
        CoderAgent(provider=coder_provider).run(context)

        tester_provider = FakeProvider([FENCED_TEST])
        result = TesterAgent(provider=tester_provider).run(context)

        assert result.success is True
        assert "2 passed" in result.metadata["pytest_output"]
        assert context.memory["test_passed"] is True


def test_tester_agent_reports_failure_when_llm_generated_tests_fail():
    with tempfile.TemporaryDirectory() as workspace_dir:
        context = AgentContext(task="write an add function", history=[])
        context.memory["workspace_dir"] = workspace_dir
        context.memory["code"] = "def add(a: int, b: int) -> int:\n    return a - b\n"  # bug

        broken_test = (
            "```python\n"
            "from solution import add\n\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
            "```\n"
        )
        tester_provider = FakeProvider([broken_test])
        result = TesterAgent(provider=tester_provider).run(context)

        assert result.success is False
        assert context.memory["test_passed"] is False