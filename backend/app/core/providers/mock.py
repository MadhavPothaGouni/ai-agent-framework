from app.core.providers.base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, messages: list[dict[str, str]]) -> str:
        turn = len(messages)
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return f"[mock-planner] (turn {turn}) received: {last_user}"