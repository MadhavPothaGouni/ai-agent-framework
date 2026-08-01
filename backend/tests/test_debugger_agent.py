from app.agents.base import AgentContext
from app.agents.debugger import DebuggerAgent


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.last_prompt = None

    def complete(self, messages):
        self.last_prompt = messages[-1]["content"]
        return "Root cause: off-by-one. Fix: use <= instead of <."


def test_debugger_heuristic_identifies_known_exception_with_mock_provider():
    context = AgentContext(task="build a calculator")
    context.memory["code"] = "def solution(a, b):\n    return a - b\n"
    context.memory["last_test_output"] = (
        "E       AssertionError: assert -1 == 5\n"
        "solution.py:2: AssertionError"
    )

    result = DebuggerAgent().run(context)  # no provider injected -> defaults to mock

    assert result.success is True
    assert "AssertionError" in result.output
    assert "Diagnosis:" in result.output
    assert context.memory["debug_diagnosis"] == result.output


def test_debugger_heuristic_handles_output_with_no_known_exception():
    context = AgentContext(task="build a calculator")
    context.memory["code"] = "def solution(a, b):\n    return a - b\n"
    context.memory["last_test_output"] = "1 failed in 0.01s"

    result = DebuggerAgent().run(context)

    assert result.success is True
    assert "no recognizable Python exception type" in result.output


def test_debugger_uses_real_provider_when_injected():
    fake = FakeProvider()
    context = AgentContext(task="build a calculator")
    context.memory["code"] = "def solution(a, b):\n    return a - b\n"
    context.memory["last_test_output"] = "AssertionError: assert -1 == 5"

    result = DebuggerAgent(provider=fake).run(context)

    assert result.output == "Root cause: off-by-one. Fix: use <= instead of <."
    assert result.metadata["provider"] == "fake"
    # The real code + failure output should have been included in the prompt
    # sent to the provider, not just a generic instruction.
    assert "AssertionError" in fake.last_prompt
    assert "def solution" in fake.last_prompt