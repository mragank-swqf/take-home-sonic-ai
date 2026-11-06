from datetime import date, datetime, timezone
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "sonic_acme"
    data_dir: str = "/app/data"

    cors_origins: str = "http://127.0.0.1:3000"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    org_mailbox_address: str = ""
    imap_poll_interval_seconds: int = 60
    reminder_cooldown_minutes: int = 5

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_min_confidence: float = 0.70

    demo_as_of_date: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def as_of_date(self) -> date:
        raw = (self.demo_as_of_date or "").strip()
        if raw:
            return date.fromisoformat(raw)
        return datetime.now(timezone.utc).date()


@lru_cache
def get_settings() -> Settings:
    return Settings()
