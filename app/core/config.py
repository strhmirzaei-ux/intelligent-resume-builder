from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Intelligent Persian Resume Builder"
    debug: bool = False
    llm_api_key: str | None = None
    llm_base_url: str = "https://model.inferx.net/endpoints/v1"
    llm_model: str = "Qwen3.6-35B-A3B-FP8"
    max_input_length: int = 20_000
    llm_timeout_seconds: float = 45.0
    llm_max_output_tokens: int = 3_000
    session_ttl_seconds: int = 86_400
    storage_path: str = "data/sessions"
    database_url: str | None = None
    database_auto_create: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
