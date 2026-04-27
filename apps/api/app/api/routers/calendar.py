"""Calendar router — Google Calendar integration for AI-Life travel planning.

Endpoints:
- GET /calendar/travel-calendar: metadata of the AI-Life travel calendar
- POST /calendar/sync-travel: sync commute/travel events based on upcoming events
- GET /calendar/upcoming: list upcoming events from primary calendar (debug aid)
- GET /calendar/plan-for-event/{event_id}: ad-hoc commute plan for a single event

Autonomy boundary: sync-travel writes to a DEDICATED travel calendar only,
never to the user's primary calendar. All writes are idempotent.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.google_calendar_service import GoogleCalendarService


router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService()


@router.get("/travel-calendar")
def get_travel_calendar_metadata(
    service: GoogleCalendarService = Depends(get_calendar_service),
) -> dict:
    """Get metadata of the AI-Life travel calendar (creates it if missing)."""
    try:
        calendar_id = service.ensure_travel_calendar()
        return {
            "id": calendar_id,
            "summary": "AI-Life — Travel",
            "description": "Auto-managed commute and travel events",
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to access travel calendar: {e}") from e


@router.post("/sync-travel")
def sync_travel_events(
    dry_run: bool = Query(False, description="Preview changes without writing to Google Calendar"),
    service: GoogleCalendarService = Depends(get_calendar_service),
) -> dict:
    """Sync travel/commute events to the travel calendar.

    Reads the next 7 days of events from the primary calendar. For any event
    at a work location, computes a leave-at time and upserts a corresponding
    "🚌 Leave for <event>" event on the travel calendar.

    Idempotent: re-running with the same input updates rather than duplicates.

    Query params:
    - dry_run=true: preview changes without writing
    """
    try:
        stats = service.sync_travel_events(dry_run=dry_run)
        return {
            "dry_run": dry_run,
            "stats": stats,
            "message": (
                "Sync preview complete (no changes written)"
                if dry_run
                else "Travel calendar synced successfully"
            ),
        }
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {e}") from e


@router.get("/upcoming")
def list_upcoming_events(
    days: int = Query(7, ge=1, le=90, description="Number of days to look ahead"),
    calendar_id: str = Query("primary", description="Calendar ID to read from"),
    service: GoogleCalendarService = Depends(get_calendar_service),
) -> dict:
    """List upcoming events from the specified calendar (debug aid)."""
    try:
        events = service.list_upcoming_events(calendar_id=calendar_id, days=days)
        return {
            "calendar_id": calendar_id,
            "days": days,
            "count": len(events),
            "events": [
                {
                    "id": ev["id"],
                    "summary": ev.get("summary", "(no title)"),
                    "start": ev.get("start", {}),
                    "location": ev.get("location", ""),
                }
                for ev in events
            ],
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to list events: {e}") from e


@router.get("/plan-for-event/{event_id}")
def plan_for_event(
    event_id: str,
    service: GoogleCalendarService = Depends(get_calendar_service),
) -> dict:
    """Ad-hoc commute plan for a single event (future enhancement).

    For now, returns a placeholder. Full implementation would call
    transit_service.suggest_commute with the event's location and time.
    """
    # TODO: fetch event by ID, extract location & time, call transit service
    return {
        "event_id": event_id,
        "message": "Ad-hoc planning not yet implemented. Use POST /calendar/sync-travel instead.",
    }
