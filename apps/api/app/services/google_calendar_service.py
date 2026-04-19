"""Google Calendar service for AI-Life.

Responsibilities:
- Load stored OAuth user credentials (bootstrapped once via the CLI).
- Ensure a dedicated secondary calendar exists ("AI-Life — Travel") so automated
  events stay visually distinct and are trivially revertible.
- Upsert trip events idempotently keyed by Concur trip ID via
  extendedProperties.private.tripId.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.settings import Settings, get_settings


TRAVEL_CALENDAR_SUMMARY = "AI-Life — Travel"
TRIP_ID_PROP = "tripId"
EVENT_KIND_PROP = "aiLifeEventKind"  # e.g. "flight", "trip-window", "travel-buffer"


class GoogleCalendarService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._creds: Optional[Credentials] = None
        self._service: Any = None

    # --- auth -----------------------------------------------------------------
    def _load_credentials(self) -> Credentials:
        token_path: Path = self.settings.google_oauth_token_file
        if not token_path.exists():
            raise RuntimeError(
                f"No Google OAuth token at {token_path}. "
                "Run `python -m app.cli.google_auth` once to grant consent."
            )
        creds = Credentials.from_authorized_user_file(
            str(token_path), self.settings.google_oauth_scopes
        )
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json())
            else:
                raise RuntimeError(
                    "Stored Google credentials are invalid and cannot be refreshed. "
                    "Re-run `python -m app.cli.google_auth`."
                )
        return creds

    @property
    def service(self) -> Any:
        if self._service is None:
            self._creds = self._load_credentials()
            self._service = build("calendar", "v3", credentials=self._creds, cache_discovery=False)
        return self._service

    # --- calendar management --------------------------------------------------
    def ensure_travel_calendar(self) -> str:
        """Return the calendarId for the AI-Life travel calendar, creating it if missing.

        Persists the ID back into .secrets/travel_calendar_id for subsequent runs.
        """
        cached_id = self.settings.ai_life_travel_calendar_id
        if cached_id:
            return cached_id

        id_cache = self.settings.google_oauth_token_file.parent / "travel_calendar_id"
        if id_cache.exists():
            return id_cache.read_text().strip()

        # Search existing calendars first (idempotent across re-runs).
        page_token = None
        while True:
            resp = self.service.calendarList().list(pageToken=page_token).execute()
            for entry in resp.get("items", []):
                if entry.get("summary") == TRAVEL_CALENDAR_SUMMARY:
                    id_cache.write_text(entry["id"])
                    return entry["id"]
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        created = self.service.calendars().insert(
            body={
                "summary": TRAVEL_CALENDAR_SUMMARY,
                "description": "Auto-managed by AI-Life. Trip events derived from Concur itineraries.",
                "timeZone": "Europe/London",
            }
        ).execute()
        id_cache.write_text(created["id"])
        return created["id"]

    # --- event upsert ---------------------------------------------------------
    @staticmethod
    def _matches_trip_event(event: dict, trip_id: str, kind: str) -> bool:
        props = (event.get("extendedProperties") or {}).get("private") or {}
        return props.get(TRIP_ID_PROP) == trip_id and props.get(EVENT_KIND_PROP) == kind

    def upsert_event(
        self,
        *,
        calendar_id: str,
        trip_id: str,
        kind: str,
        body: dict,
    ) -> dict:
        """Insert or update an event keyed by (tripId, kind).

        `body` is a Google Calendar event resource; this method injects the
        extendedProperties needed for idempotency.
        """
        body = dict(body)
        ext = body.setdefault("extendedProperties", {})
        private = ext.setdefault("private", {})
        private[TRIP_ID_PROP] = trip_id
        private[EVENT_KIND_PROP] = kind

        existing = self._find_event(calendar_id, trip_id, kind)
        if existing:
            return self.service.events().update(
                calendarId=calendar_id, eventId=existing["id"], body=body
            ).execute()
        return self.service.events().insert(calendarId=calendar_id, body=body).execute()

    def _find_event(self, calendar_id: str, trip_id: str, kind: str) -> Optional[dict]:
        try:
            resp = self.service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty=[f"{TRIP_ID_PROP}={trip_id}", f"{EVENT_KIND_PROP}={kind}"],
                maxResults=5,
                showDeleted=False,
                singleEvents=True,
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Calendar lookup failed: {e}") from e
        items = resp.get("items", [])
        return items[0] if items else None

    def delete_trip_events(self, *, calendar_id: str, trip_id: str) -> int:
        """Remove all events for a given trip. Returns number deleted."""
        resp = self.service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=[f"{TRIP_ID_PROP}={trip_id}"],
            maxResults=250,
            showDeleted=False,
            singleEvents=True,
        ).execute()
        count = 0
        for ev in resp.get("items", []):
            self.service.events().delete(calendarId=calendar_id, eventId=ev["id"]).execute()
            count += 1
        return count
