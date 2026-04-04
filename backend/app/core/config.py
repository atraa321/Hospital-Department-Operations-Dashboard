from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Case Disease Analytics API"
    app_env: str = "dev"
    app_port: int = 18080
    debug: bool = True
    database_url: str
    data_root: str = "./data"
    db_bootstrap_on_startup: bool = True
    db_schema_guards_on_startup: bool = True
    upload_dir: str = "./data/uploads"
    export_dir: str = "./data/exports"
    log_dir: str = "./logs"
    max_upload_mb: int = 100
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    auth_mode: str = "dev_header"
    auth_identity_header: str = "X-Remote-User"
    auth_user_map_file: str = "./config/auth_users.json"
    auth_trusted_proxy_ips: list[str] = ["127.0.0.1", "::1"]
    auth_allow_unmapped_viewer: bool = False
    import_queue_poll_seconds: int = 3
    import_queue_limit: int = 20
    import_task_timeout_seconds: int = 3600
    import_default_row_limit: int = 200000
    import_cost_detail_row_limit: int = 800000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return []

    @field_validator("auth_trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()

