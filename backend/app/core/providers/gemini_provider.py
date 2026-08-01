"""Real provider backed by Google's Gemini API.

Only imported/instantiated when LLM_PROVIDER=gemini — the `google-genai`
package is not a hard dependency of the base project.

Note: Gemini's chat format calls the assistant role "model" rather than
"assistant" — that's translated here so callers don't need to care.
"""
from app.core.config import get_settings
from app.core.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "The 'google-genai' package is not installed. Run: pip install google-genai"
            ) from exc

        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")

        self._client = genai.Client(api_key=settings.gemini_api_key)

    def complete(self, messages: list[dict[str, str]]) -> str:
        contents = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
            if m["role"] in ("user", "assistant")
        ]

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Gemini API call failed: {exc}. Check GEMINI_API_KEY and network access."
            ) from exc

        return response.text or ""