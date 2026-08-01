"""Real provider backed by the OpenAI API.

Only imported/instantiated when LLM_PROVIDER=openai — the `openai`
package is not a hard dependency of the base project.
"""
from app.core.config import get_settings
from app.core.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in .env")

        self._client = openai.OpenAI(api_key=settings.openai_api_key)

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model="gpt-4.1",
                max_tokens=1536,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in messages
                    if m["role"] in ("user", "assistant")
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"OpenAI API call failed: {exc}. Check OPENAI_API_KEY and network access."
            ) from exc

        return response.choices[0].message.content or ""