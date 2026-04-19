"""Trip domain schemas.

A Trip is the canonical, provider-agnostic representation of a business trip
derived from a Concur / TripIt itinerary. It is deliberately decoupled from
both the capture method (forward rule, TripIt feed, manual) and from Google
Calendar so downstream consumers (Home Assistant, Renewal Engine) can react to
a single stable shape.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TripEventKind(str, Enum):
    TRIP_WINDOW = "trip-window"       # all-day spanning Away block
    FLIGHT = "flight"
    HOTEL = "hotel"
    GROUND = "ground"                 # taxi / rail / rental
    TRAVEL_BUFFER = "travel-buffer"   # home→airport, arrival→hotel


class Flight(BaseModel):
    carrier: str
    flight_number: str
    origin_iata: str
    destination_iata: str
    depart_local: datetime
    arrive_local: datetime
    depart_tz: str = "Europe/London"
    arrive_tz: str = "Europe/London"
    confirmation_code: Optional[str] = None


class Hotel(BaseModel):
    name: str
    address: Optional[str] = None
    check_in_local: datetime
    check_out_local: datetime
    tz: str = "Europe/London"
    confirmation_code: Optional[str] = None


class Trip(BaseModel):
    """Canonical trip record. `id` should be the Concur/TripIt trip ID when available."""

    id: str = Field(..., description="Stable trip identifier (Concur trip ID preferred)")
    title: str = Field(..., description="Human label, e.g. 'London → New York'")
    start_local: datetime
    end_local: datetime
    tz: str = "Europe/London"
    flights: list[Flight] = Field(default_factory=list)
    hotels: list[Hotel] = Field(default_factory=list)
    source: str = Field("manual", description="concur | tripit | manual")
    notes: Optional[str] = None


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class TripApproval(BaseModel):
    trip: Trip
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    google_calendar_id: Optional[str] = None
    event_ids: list[str] = Field(default_factory=list)
