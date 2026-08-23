from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INTENTFENCE_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite:///./intentfence.db"
    cors_origins: str = "http://localhost:3000"
    semantic_ollama_base_url: str = "http://localhost:11434"
    semantic_ollama_model: str = "qwen2.5:7b"
    semantic_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    agent_ollama_base_url: str = "http://127.0.0.1:11434"
    agent_ollama_model: str = "qwen3:14b"
    agent_ollama_context_length: int = Field(default=32768, ge=4096, le=262144)
    agent_ollama_timeout_seconds: float = Field(default=300.0, gt=0.0, le=900.0)
    live_web_enabled: bool = False
    ollama_api_key: str | None = None
    ollama_web_base_url: str = "https://ollama.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
