"""Observability bootstrap — Sentry for FastAPI.

No-ops cleanly when SENTRY_DSN is unset (local dev without creds).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.settings import Settings


def init_sentry(settings: "Settings") -> None:
    """Initialize Sentry if a DSN is configured. Silent no-op otherwise."""
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        # sentry-sdk not installed; fail quietly so local dev without it still works.
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        # PII scrubbing: never capture request bodies or headers that could leak tokens.
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
