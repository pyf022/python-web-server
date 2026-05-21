from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "python-ai-tool-server"
    api_keys: str = Field(default="dev-api-key", description="Comma-separated API keys.")
    redis_url: str = "redis://localhost:6379/0"
    storage_root: Path = Path("./data")
    public_base_url: str = "http://localhost:8000"
    job_timeout_seconds: int = 300
    file_ttl_seconds: int = 24 * 60 * 60
    webhook_timeout_seconds: int = 10

    @property
    def api_key_set(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
