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
    semantic_enabled: bool = False
    semantic_ollama_base_url: str = "http://localhost:11434"
    semantic_ollama_model: str = "qwen2.5:7b"
    semantic_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
