from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_sandbox_tag_key: str = "quorom:managed"
    aws_sandbox_tag_value: str = "true"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    database_url: str = "sqlite:///./quorom.db"
    # mock | live
    quorom_mode: str = "mock"
    dry_run: bool = True
    lookback_days: int = 7
    idle_cpu_threshold_pct: float = 5.0
    oversize_cpu_peak_pct: float = 20.0
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sandbox_tag_filter(self) -> dict[str, str]:
        return {self.aws_sandbox_tag_key: self.aws_sandbox_tag_value}


@lru_cache
def get_settings() -> Settings:
    return Settings()
