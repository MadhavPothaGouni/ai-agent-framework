
import sys
import types

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_provider(monkeypatch, name: str, **extra_env: str) -> None:
    monkeypatch.setenv("LLM_PROVIDER", name)
    for key, value in extra_env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_defaults_to_mock(monkeypatch):
    _set_provider(monkeypatch, "mock")
    from app.core.providers import get_provider
    from app.core.providers.mock import MockProvider

    assert isinstance(get_provider(), MockProvider)


def test_factory_rejects_unknown_provider_name(monkeypatch):
    _set_provider(monkeypatch, "not-a-real-provider")
    from app.core.providers import get_provider

    with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER"):
        get_provider()


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


def test_openai_provider_raises_when_package_missing(monkeypatch):
    _set_provider(monkeypatch, "openai", OPENAI_API_KEY="sk-test")
    monkeypatch.delitem(sys.modules, "openai", raising=False)
    monkeypatch.setitem(sys.modules, "openai", None)  # force ImportError

    from app.core.providers.openai_provider import OpenAIProvider

    with pytest.raises(RuntimeError, match="not installed"):
        OpenAIProvider()


def test_openai_provider_raises_when_key_missing(monkeypatch):
    _set_provider(monkeypatch, "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = lambda api_key: object()
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    from app.core.providers.openai_provider import OpenAIProvider

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIProvider()


def test_openai_provider_complete_happy_path(monkeypatch):
    _set_provider(monkeypatch, "openai", OPENAI_API_KEY="sk-test")

    captured = {}

    class FakeMessage:
        content = "hi, how are you?"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, model, max_tokens, messages):
            captured["model"] = model
            captured["max_tokens"] = max_tokens
            captured["messages"] = messages
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.chat = FakeChat()

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    from app.core.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider()
    reply = provider.complete(
        [
            {"role": "system", "content": "ignored by filter"},
            {"role": "user", "content": "hi"},
        ]
    )

    assert reply == "hi, how are you?"
    assert captured["api_key"] == "sk-test"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_openai_provider_wraps_api_errors(monkeypatch):
    _set_provider(monkeypatch, "openai", OPENAI_API_KEY="sk-test")

    class BoomCompletions:
        def create(self, **kwargs):
            raise ValueError("network exploded")

    class FakeChat:
        completions = BoomCompletions()

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = FakeChat()

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    from app.core.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider()
    with pytest.raises(RuntimeError, match="OpenAI API call failed"):
        provider.complete([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


def _uninstall_fake_google_genai(monkeypatch):
    monkeypatch.delitem(sys.modules, "google.genai", raising=False)
    google_mod = sys.modules.get("google")
    if google_mod is not None and hasattr(google_mod, "genai"):
        monkeypatch.delattr(google_mod, "genai", raising=False)


def test_gemini_provider_raises_when_package_missing(monkeypatch):
    _set_provider(monkeypatch, "gemini", GEMINI_API_KEY="test-key")
    _uninstall_fake_google_genai(monkeypatch)

    from app.core.providers.gemini_provider import GeminiProvider

    with pytest.raises(RuntimeError, match="not installed"):
        GeminiProvider()


def _install_fake_google_genai(monkeypatch, client_factory):
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = client_factory
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    google_mod = sys.modules.get("google")
    if google_mod is None:
        google_mod = types.ModuleType("google")
        monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setattr(google_mod, "genai", fake_genai, raising=False)


def test_gemini_provider_raises_when_key_missing(monkeypatch):
    _set_provider(monkeypatch, "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()

    _install_fake_google_genai(monkeypatch, client_factory=lambda api_key: object())

    from app.core.providers.gemini_provider import GeminiProvider

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_gemini_provider_complete_happy_path(monkeypatch):
    _set_provider(monkeypatch, "gemini", GEMINI_API_KEY="test-key")

    captured = {}

    class FakeResponse:
        text = "hi, how are you?"

    class FakeModels:
        def generate_content(self, model, contents):
            captured["model"] = model
            captured["contents"] = contents
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    _install_fake_google_genai(monkeypatch, client_factory=FakeClient)

    from app.core.providers.gemini_provider import GeminiProvider

    provider = GeminiProvider()
    reply = provider.complete(
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "previous reply"},
        ]
    )

    assert reply == "hi, how are you?"
    assert captured["api_key"] == "test-key"
    # Gemini calls the assistant role "model", not "assistant".
    assert captured["contents"] == [
        {"role": "user", "parts": [{"text": "hi"}]},
        {"role": "model", "parts": [{"text": "previous reply"}]},
    ]


def test_gemini_provider_wraps_api_errors(monkeypatch):
    _set_provider(monkeypatch, "gemini", GEMINI_API_KEY="test-key")

    class BoomModels:
        def generate_content(self, **kwargs):
            raise ValueError("network exploded")

    class FakeClient:
        def __init__(self, api_key):
            self.models = BoomModels()

    _install_fake_google_genai(monkeypatch, client_factory=FakeClient)

    from app.core.providers.gemini_provider import GeminiProvider

    provider = GeminiProvider()
    with pytest.raises(RuntimeError, match="Gemini API call failed"):
        provider.complete([{"role": "user", "content": "hi"}])