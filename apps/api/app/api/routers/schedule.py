"""
Schedule Advisor Router

Exposes "when to leave" recommendations based on location + calendar + transit.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.schedule_advisor_service import ScheduleAdvisorService
from app.services.airport_advisor_service import (
    AirportAdvisorService,
    Mode as AirportMode,
)
from app.services.trip_store import TripStore, get_trip_store
from typing import Optional

router = APIRouter(prefix="/schedule", tags=["schedule"])


def get_schedule_service():
    return ScheduleAdvisorService()


def get_airport_service() -> AirportAdvisorService:
    return AirportAdvisorService()


@router.get("/when-to-leave")
async def get_when_to_leave_advice(
    person_id: str = Query(default="declan", description="Person entity ID from Home Assistant"),
    lookahead_hours: int = Query(default=4, ge=1, le=24, description="Hours to look ahead for next event")
):
    """
    Get proactive "when to leave" advice based on:
    - Current location (Home Assistant presence)
    - Next calendar event (Google Calendar)
    - Real-time transit (TFI GTFS-R)
    
    Returns approval-card shaped recommendation with urgency status.
    
    Example response:
    ```json
    {
        "advice": "Leave at 13:42 to catch the 15A",
        "current_location": "home",
        "location_zone": "home",
        "destination_zone": "harcourt",
        "next_event": {
            "summary": "Team Meeting",
            "location": "Harcourt St, Dublin",
            "start": "2026-04-25T14:30:00+00:00"
        },
        "transit_options": [
            {
                "route": "15A",
                "mode": "bus",
                "departure_time": "13:47",
                "arrival_time": "14:22",
                "travel_minutes": 35
            }
        ],
        "recommended_departure": "2026-04-25T13:42:00+00:00",
        "minutes_until_depart": 12,
        "status": "on_time"
    }
    ```
    
    Status values:
    - `on_time`: Plenty of time (>15 min)
    - `tight`: Should leave soon (5-15 min)
    - `urgent`: Leave immediately (<5 min)
    - `missed`: Already late
    - `relaxed`: No upcoming events
    - `unknown_location`: Can't determine origin/destination
    - `no_transit`: No transit options found
    - `error`: Service error
    """
    try:
        service = get_schedule_service()
        advice = service.get_next_departure_advice(
            person_id=person_id,
            lookahead_hours=lookahead_hours
        )
        return advice
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating departure advice: {str(e)}"
        )


@router.get("/leave-for-airport")
async def get_leave_for_airport_advice(
    trip_id: Optional[str] = Query(
        default=None,
        description="Trip ID — looks up the first flight on that trip.",
    ),
    depart_local: Optional[datetime] = Query(
        default=None,
        description="Scheduled flight departure (timezone-aware). Required if trip_id is omitted.",
    ),
    origin_iata: Optional[str] = Query(
        default=None,
        description="Origin airport IATA. Required if trip_id is omitted.",
    ),
    destination_iata: Optional[str] = Query(
        default=None,
        description="Destination airport IATA. Required if trip_id is omitted.",
    ),
    mode: AirportMode = Query(
        default=AirportMode.TAXI,
        description="How you'll get to the airport (drive | taxi | aircoach | dart | bus).",
    ),
    travel_time_override_min: Optional[int] = Query(
        default=None,
        description="Override default mode travel time. Use when caller has a live ETA.",
    ),
    store: TripStore = Depends(get_trip_store),
    advisor: AirportAdvisorService = Depends(get_airport_service),
):
    """Compute when to leave home for the airport.

    Two modes:
    - `trip_id` — looks up the first flight on the trip (recommended).
    - explicit `depart_local + origin_iata + destination_iata` — ad-hoc.

    Returns leave-by time + a full breakdown so the UI can show *why*
    (check-in close, security, transfer, travel, personal buffer).

    Honest caveat: travel time is a static profile estimate, not traffic-aware.
    Confidence is reported as `estimate` until a live ETA is plugged in.
    """
    if trip_id:
        approval = store.get(trip_id)
        if not approval:
            raise HTTPException(404, f"trip {trip_id} not found")
        if not approval.trip.flights:
            raise HTTPException(400, f"trip {trip_id} has no flights")
        flight = approval.trip.flights[0]
        depart_local = flight.depart_local
        origin_iata = flight.origin_iata
        destination_iata = flight.destination_iata
    else:
        if not (depart_local and origin_iata and destination_iata):
            raise HTTPException(
                400,
                "Provide either trip_id, or all of depart_local + origin_iata + destination_iata.",
            )

    if depart_local.tzinfo is None:
        raise HTTPException(400, "depart_local must include a timezone offset.")

    advice = advisor.advise(
        depart_local=depart_local,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        mode=mode,
        travel_time_override_min=travel_time_override_min,
    )

    return {
        "trip_id": trip_id,
        "leave_by_local": advice.leave_by_local.isoformat(),
        "depart_local": advice.depart_local.isoformat(),
        "origin_iata": advice.origin_iata,
        "destination_iata": advice.destination_iata,
        "confidence": advice.confidence,
        "data_sources": advice.data_sources,
        "notes": advice.notes,
        "breakdown": {
            "flight_category": advice.breakdown.flight_category.value,
            "mode": advice.breakdown.mode.value,
            "is_peak": advice.breakdown.is_peak,
            "check_in_close_min": advice.breakdown.check_in_close_min,
            "security_min": advice.breakdown.security_min,
            "transfer_to_gate_min": advice.breakdown.transfer_to_gate_min,
            "travel_time_min": advice.breakdown.travel_time_min,
            "personal_buffer_min": advice.breakdown.personal_buffer_min,
            "total_offset_min": advice.breakdown.total_offset_min,
        },
    }


@router.get("/health")
async def health_check():
    """Health check for schedule advisor service."""
    try:
        service = get_schedule_service()
        
        # Test each sub-service
        checks = {
            "home_assistant": False,
            "google_calendar": False,
            "transit": False
        }
        
        try:
            service.ha_service.get_person_state("declan")
            checks["home_assistant"] = True
        except:
            pass
        
        try:
            service.calendar_service.list_events(max_results=1)
            checks["google_calendar"] = True
        except:
            pass
        
        try:
            service.transit_service.get_bus_departures("4513")
            checks["transit"] = True
        except:
            pass
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": checks
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )
