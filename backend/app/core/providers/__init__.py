from app.core.config import get_settings
from app.core.providers.base import LLMProvider
from app.core.providers.mock import MockProvider


def get_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "anthropic":
        from app.core.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    return MockProvider()