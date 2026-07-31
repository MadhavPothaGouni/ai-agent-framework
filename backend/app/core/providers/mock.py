from app.core.providers.base import LLMProvider

_CODE_MARKER = "You are a coding agent"

_MOCK_SOLUTION = '''"""Mock generated implementation.

This fixed snippet exists so the framework runs end-to-end with zero
API keys configured. Swap in a real LLMProvider (e.g. Anthropic) to
get actual generated code for the task.
"""


def solution(a: int, b: int) -> int:
    return a + b
'''


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, messages: list[dict[str, str]]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )

        if _CODE_MARKER in last_user:
            return _MOCK_SOLUTION

        turn = len(messages)
        return f"[mock-planner] (turn {turn}) received: {last_user}"