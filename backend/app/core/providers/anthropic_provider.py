from app.core.config import get_settings
from app.core.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Run: pip install anthropic"
            ) from exc

        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self._client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] in ("user", "assistant")
            ],
        )
        return response.content[0].text