"""Trip approval service.

Translates a canonical Trip into Google Calendar events on the AI-Life travel
calendar. All writes are idempotent keyed by (tripId, kind), so re-applying
the same trip is safe.

Autonomy boundary: this service ONLY executes when called via an explicit
approval (/trips/{id}/approve). The parser layer never writes to the calendar
directly — it only produces pending TripApproval records.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.schemas.trip import (
    ApprovalStatus,
    Flight,
    Hotel,
    Trip,
    TripApproval,
    TripEventKind,
)
from app.services.google_calendar_service import GoogleCalendarService


class TripApprovalService:
    def __init__(self, calendar: Optional[GoogleCalendarService] = None) -> None:
        self.calendar = calendar or GoogleCalendarService()

    def apply(self, approval: TripApproval) -> TripApproval:
        """Write all events for an approved trip. Returns the updated approval."""
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError("Trip must be APPROVED before calendar apply")

        calendar_id = self.calendar.ensure_travel_calendar()
        trip = approval.trip
        event_ids: list[str] = []

        # 1) All-day trip window
        window = self.calendar.upsert_event(
            calendar_id=calendar_id,
            trip_id=trip.id,
            kind=TripEventKind.TRIP_WINDOW.value,
            body={
                "summary": f"Away — {trip.title}",
                "description": trip.notes or "Business travel (AI-Life auto-sync)",
                "start": {"date": trip.start_local.date().isoformat()},
                "end": {"date": (trip.end_local.date() + timedelta(days=1)).isoformat()},
                "transparency": "opaque",
            },
        )
        event_ids.append(window["id"])

        # 2) Flights
        for idx, flight in enumerate(trip.flights):
            ev = self.calendar.upsert_event(
                calendar_id=calendar_id,
                trip_id=trip.id,
                kind=f"{TripEventKind.FLIGHT.value}:{idx}",
                body=_flight_event_body(flight),
            )
            event_ids.append(ev["id"])

        # 3) Hotels
        for idx, hotel in enumerate(trip.hotels):
            ev = self.calendar.upsert_event(
                calendar_id=calendar_id,
                trip_id=trip.id,
                kind=f"{TripEventKind.HOTEL.value}:{idx}",
                body=_hotel_event_body(hotel),
            )
            event_ids.append(ev["id"])

        approval.status = ApprovalStatus.APPLIED
        approval.applied_at = datetime.utcnow()
        approval.google_calendar_id = calendar_id
        approval.event_ids = event_ids
        return approval

    def revert(self, approval: TripApproval) -> int:
        calendar_id = approval.google_calendar_id or self.calendar.ensure_travel_calendar()
        return self.calendar.delete_trip_events(calendar_id=calendar_id, trip_id=approval.trip.id)


def _flight_event_body(flight: Flight) -> dict:
    summary = f"✈️ {flight.carrier}{flight.flight_number} {flight.origin_iata} → {flight.destination_iata}"
    desc_lines = [
        f"Flight {flight.carrier}{flight.flight_number}",
        f"{flight.origin_iata} → {flight.destination_iata}",
    ]
    if flight.confirmation_code:
        desc_lines.append(f"Confirmation: {flight.confirmation_code}")
    return {
        "summary": summary,
        "description": "\n".join(desc_lines),
        "location": f"{flight.origin_iata} ({flight.carrier}{flight.flight_number})",
        "start": {"dateTime": flight.depart_local.isoformat(), "timeZone": flight.depart_tz},
        "end": {"dateTime": flight.arrive_local.isoformat(), "timeZone": flight.arrive_tz},
    }


def _hotel_event_body(hotel: Hotel) -> dict:
    desc = []
    if hotel.address:
        desc.append(hotel.address)
    if hotel.confirmation_code:
        desc.append(f"Confirmation: {hotel.confirmation_code}")
    return {
        "summary": f"🏨 {hotel.name}",
        "description": "\n".join(desc),
        "location": hotel.address or hotel.name,
        "start": {"dateTime": hotel.check_in_local.isoformat(), "timeZone": hotel.tz},
        "end": {"dateTime": hotel.check_out_local.isoformat(), "timeZone": hotel.tz},
    }
