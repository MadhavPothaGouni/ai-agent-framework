
from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.providers import get_metered_provider
from app.core.providers.base import LLMProvider

# Ordered roughly by how commonly they show up in a first-attempt LLM
# code-gen failure — first match wins for the heuristic summary.
_KNOWN_EXCEPTIONS = [
    "SyntaxError",
    "IndentationError",
    "ModuleNotFoundError",
    "ImportError",
    "NameError",
    "AttributeError",
    "TypeError",
    "ValueError",
    "KeyError",
    "IndexError",
    "ZeroDivisionError",
    "AssertionError",
]


def _heuristic_diagnosis(failure_output: str) -> str:
    found = next((exc for exc in _KNOWN_EXCEPTIONS if exc in failure_output), None)

    if found is None:
        return (
            "Diagnosis: tests failed but no recognizable Python exception type "
            "was found in the output. Re-check the implementation against the "
            "plan's requirements (likely a logic mismatch, not a crash).\n\n"
            f"Raw failure:\n{failure_output}"
        )

    return (
        f"Diagnosis: the previous attempt raised a {found}. Review the "
        "traceback below, fix the underlying cause (not just the symptom), "
        "and keep the same function/class names the tests import.\n\n"
        f"Raw failure:\n{failure_output}"
    )


class DebuggerAgent(BaseAgent):
    name = "debugger"

    def __init__(self, provider: LLMProvider | None = None) -> None:
        # Injectable so tests can supply a fake provider instead of hitting
        # a real API; defaults to whatever LLM_PROVIDER is configured.
        self._provider = provider

    def run(self, context: AgentContext) -> AgentResult:
        provider = self._provider or get_metered_provider()
        code = context.memory.get("code", "")
        failure_output = context.memory.get("last_test_output", "")

        if provider.name == "mock":
            diagnosis = _heuristic_diagnosis(failure_output)
        else:
            prompt = (
                "You are a debugging agent. A test run just failed for this code:\n\n"
                f"Code:\n{code}\n\n"
                f"Test failure output:\n{failure_output}\n\n"
                "In 2-4 sentences: diagnose the root cause, then state the "
                "concrete fix needed. Be specific and concise — this will be "
                "handed directly to another agent to act on."
            )
            diagnosis = provider.complete([{"role": "user", "content": prompt}])

        context.memory["debug_diagnosis"] = diagnosis
        return AgentResult(output=diagnosis, success=True, metadata={"provider": provider.name})