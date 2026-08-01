"""Application settings, loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "changeme"

    database_url: str = "postgresql://user:password@localhost:5432/agent_framework"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # "mock" (default, no API key needed), "anthropic", "openai", or "gemini"
    llm_provider: str = "mock"

    # Each workflow run gets its own subfolder here (see app/agents/orchestrator.py)
    workspace_root: str = "./agent_workspace"

    jwt_secret: str = "changeme"
    jwt_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()