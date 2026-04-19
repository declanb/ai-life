"""Central settings for the AI-Life backend.

Loads from environment / .env. Never hard-code secrets here.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


API_ROOT = Path(__file__).resolve().parent.parent  # apps/api
SECRETS_DIR = API_ROOT / ".secrets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(API_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment ("development", "preview", "production"). Auto-set by Vercel via VERCEL_ENV.
    environment: str = "development"

    # CORS: explicit origin allow-list. Comma-separated in env, e.g.
    #   CORS_ALLOW_ORIGINS="https://ai-life-web.vercel.app,http://localhost:3000"
    # Default covers local dev only; production origins MUST be set via env.
    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Google OAuth / Calendar
    google_oauth_client_file: Path = SECRETS_DIR / "google_oauth_client.json"
    google_oauth_token_file: Path = SECRETS_DIR / "google_oauth_token.json"
    google_oauth_scopes: list[str] = [
        "https://www.googleapis.com/auth/calendar",  # needed to CREATE a new calendar; events-only scope can't
    ]
    # If blank, the service will create an "AI-Life — Travel" calendar on first run and populate this.
    ai_life_travel_calendar_id: Optional[str] = None

    # OAuth bootstrap loopback port
    oauth_loopback_port: int = 8765

    # Observability — Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1


    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        """Accept either a JSON list or a comma-separated string from env."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return v  # let pydantic parse JSON
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
