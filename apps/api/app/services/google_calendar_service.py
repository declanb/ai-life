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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import google.auth
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
        self._creds: Any = None
        self._service: Any = None

    # --- auth -----------------------------------------------------------------
    def _load_credentials(self) -> Any:
        """Load credentials, preferring the local OAuth token file.

        Falls back to Application Default Credentials (ADC) when the token file
        is not present — run `gcloud auth application-default login
        --scopes=https://www.googleapis.com/auth/calendar` once to set up ADC.
        """
        token_path: Path = self.settings.google_oauth_token_file
        if token_path.exists():
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
                        "Re-run `python -m app.cli.google_auth` or `gcloud auth "
                        "application-default login --scopes=https://www.googleapis.com/auth/calendar`."
                    )
            return creds

        # Fall back to ADC
        try:
            creds, _ = google.auth.default(scopes=self.settings.google_oauth_scopes)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"No Google credentials available. Either run "
                f"`python -m app.cli.google_auth` to write {token_path}, or run "
                "`gcloud auth application-default login "
                "--scopes=https://www.googleapis.com/auth/calendar`."
            ) from exc
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

    # --- upcoming events (for commute planning) ------------------------------
    def list_upcoming_events(
        self, *, calendar_id: str = "primary", days: int = 7, max_results: int = 100
    ) -> list[dict]:
        """List upcoming events from the user's primary (or specified) calendar.

        Returns events starting within the next `days` days.
        """
        from datetime import datetime, timezone, timedelta

        time_min = datetime.now(timezone.utc).isoformat()
        time_max = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        try:
            resp = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            return resp.get("items", [])
        except HttpError as e:
            if e.resp.status in (403, 429):
                raise RuntimeError(f"Rate limit / auth error: {e}")
            raise

    def sync_travel_events(self, *, dry_run: bool = False) -> dict:
        """Sync commute/travel events to the travel calendar based on upcoming events.

        For each event in the next 7 days whose location matches a work location,
        computes a recommended leave-at time using the transit service, and
        upserts a corresponding "🚌 Leave for <event>" event on the travel calendar.

        Returns: {"created": int, "updated": int, "deleted": int, "skipped": int, "errors": list}
        """
        from app.services.transit_service import TransitService

        travel_cal_id = self.ensure_travel_calendar()
        upcoming = self.list_upcoming_events(days=7)
        work_locations = self.settings.work_locations

        stats = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": []}
        transit = TransitService()

        # Track which source events we've processed (for orphan cleanup)
        processed_source_ids: set[str] = set()

        for event in upcoming:
            event_id = event["id"]
            summary = event.get("summary", "")
            location = event.get("location", "")
            start = event.get("start", {})

            # Skip all-day events (no specific time → no commute planning needed)
            if "date" in start and "dateTime" not in start:
                stats["skipped"] += 1
                continue

            # Check if location matches any work location
            is_work_event = any(loc.lower() in location.lower() for loc in work_locations)
            if not is_work_event:
                stats["skipped"] += 1
                continue

            try:
                # Parse event start time
                event_start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))

                # Compute commute plan (simplified: use get_commute_to_work logic)
                # For now, default to 30min before event as leave-at time
                # TODO: integrate with transit_service.get_commute_to_work() for real-time planning
                leave_at_dt = event_start_dt - timedelta(minutes=30)

                # Build travel event body
                travel_event_body = {
                    "summary": f"🚌 Leave for {summary}",
                    "description": f"Transit to {location}\n\nSource event: {summary}",
                    "start": {
                        "dateTime": leave_at_dt.isoformat(),
                        "timeZone": start.get("timeZone", "Europe/Dublin"),
                    },
                    "end": {
                        "dateTime": event_start_dt.isoformat(),
                        "timeZone": start.get("timeZone", "Europe/Dublin"),
                    },
                    "extendedProperties": {
                        "private": {
                            "ai_life_source_event_id": event_id,
                            "ai_life_event_kind": "commute",
                        }
                    },
                    "transparency": "transparent",  # Don't block calendar
                }

                if not dry_run:
                    # Check if a travel event already exists for this source event
                    existing = self._find_travel_event_by_source(travel_cal_id, event_id)
                    if existing:
                        self.service.events().update(
                            calendarId=travel_cal_id,
                            eventId=existing["id"],
                            body=travel_event_body,
                        ).execute()
                        stats["updated"] += 1
                    else:
                        self.service.events().insert(
                            calendarId=travel_cal_id,
                            body=travel_event_body,
                        ).execute()
                        stats["created"] += 1

                processed_source_ids.add(event_id)

            except Exception as e:
                stats["errors"].append(f"Event {event_id} ({summary}): {str(e)}")

        # Cleanup: delete orphaned travel events (source event disappeared or moved)
        if not dry_run:
            try:
                deleted = self._cleanup_orphaned_travel_events(
                    travel_cal_id, processed_source_ids
                )
                stats["deleted"] = deleted
            except Exception as e:
                stats["errors"].append(f"Cleanup failed: {str(e)}")

        return stats

    def _find_travel_event_by_source(
        self, calendar_id: str, source_event_id: str
    ) -> Optional[dict]:
        """Find a travel event keyed by the source event ID."""
        try:
            resp = self.service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty=[
                    f"ai_life_source_event_id={source_event_id}",
                    "ai_life_event_kind=commute",
                ],
                maxResults=5,
                showDeleted=False,
                singleEvents=True,
            ).execute()
            items = resp.get("items", [])
            return items[0] if items else None
        except HttpError:
            return None

    def _cleanup_orphaned_travel_events(
        self, calendar_id: str, valid_source_ids: set[str]
    ) -> int:
        """Delete travel events whose source event no longer exists or is outside window."""
        resp = self.service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=["ai_life_event_kind=commute"],
            maxResults=250,
            showDeleted=False,
            singleEvents=True,
        ).execute()

        count = 0
        for ev in resp.get("items", []):
            props = (ev.get("extendedProperties") or {}).get("private") or {}
            source_id = props.get("ai_life_source_event_id")
            if source_id not in valid_source_ids:
                self.service.events().delete(calendarId=calendar_id, eventId=ev["id"]).execute()
                count += 1
        return count
