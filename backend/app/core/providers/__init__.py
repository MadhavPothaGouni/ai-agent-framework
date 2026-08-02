
from app.core.config import get_settings
from app.core.providers.base import LLMProvider
from app.core.providers.mock import MockProvider

_PROVIDER_NAMES = {"mock", "anthropic", "openai", "gemini"}


def get_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name not in _PROVIDER_NAMES:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER '{provider_name}'. Valid options: {sorted(_PROVIDER_NAMES)}"
        )

    if provider_name == "anthropic":
        from app.core.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    if provider_name == "openai":
        from app.core.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()

    if provider_name == "gemini":
        from app.core.providers.gemini_provider import GeminiProvider

        return GeminiProvider()

    return MockProvider()


def get_metered_provider() -> LLMProvider:
  
    from app.core.cost_tracker import MeteredProvider

    return MeteredProvider(get_provider())