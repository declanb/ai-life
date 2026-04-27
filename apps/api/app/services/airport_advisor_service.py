"""Airport Departure Advisor.

Given a flight (origin IATA, scheduled departure, optional aircraft type),
compute when the user should leave home for the airport.

Design notes:
- Pure function over deterministic buffer tables — no external HTTP calls.
- Traffic-aware travel time is intentionally NOT included yet. Mode-default
  times are used and tagged with `confidence: "estimate"` so the UI can show
  honesty. A future slice plugs in Google Maps Distance Matrix or TFI journey
  planner behind a feature flag.
- All times are timezone-aware; departure timezone comes from the Flight model.

Buffer composition (for an `away_from_home` flight):

    leave_by = depart_local
             - check_in_close
             - security_queue
             - transfer_to_gate
             - travel_time(mode, origin->airport)
             - personal_buffer

Where each component is selected from `AIRPORT_PROFILES` keyed by IATA, with
sensible fallbacks for unknown airports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class Mode(str, Enum):
    """How the user gets to the airport."""
    DRIVE = "drive"
    TAXI = "taxi"
    AIRCOACH = "aircoach"   # DUB / Cork / Belfast coach service
    DART = "dart"           # rail
    BUS = "bus"


class FlightCategory(str, Enum):
    SHORT_HAUL = "short_haul"   # intra-EU / UK / Schengen / domestic
    LONG_HAUL = "long_haul"     # international, requires more check-in lead time


# Iso2 country codes for short-haul from DUB (rough, good enough for buffers).
_SHORT_HAUL_DEST_PREFIXES = {
    # GB / IE
    "L", "M", "B", "E", "G",  # London (LHR/LGW/LCY/STN/LTN), Manc (MAN), Edinburgh (EDI), etc.
    # Schengen common
    "C", "F", "A", "Z", "W",
}


# ---------------------------------------------------------------------------
# Airport profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AirportProfile:
    iata: str
    name: str
    # Minutes before scheduled departure that check-in / bag-drop closes.
    check_in_close_short_haul_min: int
    check_in_close_long_haul_min: int
    # Typical security queue, peak (07:00-09:00 + 16:00-19:00 weekdays).
    security_peak_min: int
    security_offpeak_min: int
    # Walk from security exit to gate.
    transfer_to_gate_min: int
    # Default mode travel time *from the user's home* to this airport, in min.
    # Honest: these are static estimates for Coolock (Dublin 5) → airport.
    # Override by passing `travel_time_override_min` to advise().
    default_travel_time_min: dict[Mode, int] = field(default_factory=dict)


# Coolock (Dublin 5) → DUB defaults. Update if the user moves.
DUB_PROFILE = AirportProfile(
    iata="DUB",
    name="Dublin",
    check_in_close_short_haul_min=40,
    check_in_close_long_haul_min=60,
    security_peak_min=45,
    security_offpeak_min=20,
    transfer_to_gate_min=10,
    default_travel_time_min={
        Mode.DRIVE: 20,
        Mode.TAXI: 25,
        Mode.AIRCOACH: 40,
        Mode.BUS: 55,
        Mode.DART: 60,    # via bus connection
    },
)

# Generic fallback for non-DUB airports.
GENERIC_PROFILE = AirportProfile(
    iata="???",
    name="Unknown airport",
    check_in_close_short_haul_min=45,
    check_in_close_long_haul_min=75,
    security_peak_min=45,
    security_offpeak_min=25,
    transfer_to_gate_min=15,
    default_travel_time_min={
        Mode.DRIVE: 45,
        Mode.TAXI: 45,
        Mode.AIRCOACH: 60,
        Mode.BUS: 75,
        Mode.DART: 75,
    },
)

AIRPORT_PROFILES: dict[str, AirportProfile] = {
    "DUB": DUB_PROFILE,
}


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

# Crude short-haul detector based on destination IATA. Anything trans-Atlantic
# or further is long-haul. Tighten this when we have a proper airport DB.
_LONG_HAUL_DEST_HINTS = {
    # NY area
    "JFK", "EWR", "LGA",
    # US
    "BOS", "ORD", "LAX", "SFO", "SEA", "MIA", "ATL", "DFW", "IAD", "IAH",
    # Canada
    "YYZ", "YUL", "YVR",
    # Middle East
    "DXB", "AUH", "DOH",
    # Asia
    "HKG", "SIN", "NRT", "HND", "ICN", "PEK", "PVG", "BOM", "DEL",
    # Africa / S America
    "JNB", "CPT", "GRU", "EZE",
}


def _categorize_flight(destination_iata: str) -> FlightCategory:
    if destination_iata.upper() in _LONG_HAUL_DEST_HINTS:
        return FlightCategory.LONG_HAUL
    return FlightCategory.SHORT_HAUL


def _is_peak(local_dt: datetime) -> bool:
    """Weekday morning or evening peak at the airport entrance."""
    if local_dt.weekday() >= 5:  # Sat/Sun
        return False
    h = local_dt.hour
    return (5 <= h <= 9) or (15 <= h <= 19)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class AirportAdviceBreakdown:
    """Everything that went into the leave-by time. Surfaced for UI honesty."""
    flight_category: FlightCategory
    mode: Mode
    is_peak: bool
    check_in_close_min: int
    security_min: int
    transfer_to_gate_min: int
    travel_time_min: int
    personal_buffer_min: int

    @property
    def total_offset_min(self) -> int:
        return (
            self.check_in_close_min
            + self.security_min
            + self.transfer_to_gate_min
            + self.travel_time_min
            + self.personal_buffer_min
        )


@dataclass
class AirportAdvice:
    leave_by_local: datetime
    depart_local: datetime
    origin_iata: str
    destination_iata: str
    breakdown: AirportAdviceBreakdown
    confidence: str   # "estimate" | "live"  (live = traffic-aware, future)
    data_sources: list[str]
    notes: list[str]


class AirportAdvisorService:
    """Deterministic airport leave-by computation."""

    DEFAULT_PERSONAL_BUFFER_MIN = 15

    def advise(
        self,
        *,
        depart_local: datetime,
        origin_iata: str,
        destination_iata: str,
        mode: Mode = Mode.TAXI,
        travel_time_override_min: Optional[int] = None,
        personal_buffer_min: Optional[int] = None,
    ) -> AirportAdvice:
        """Compute leave-by time for a single flight.

        Args:
            depart_local: scheduled departure, timezone-aware.
            origin_iata: airport you're flying *from*.
            destination_iata: airport you're flying *to* (used for short/long haul).
            mode: how you'll get to the airport.
            travel_time_override_min: if the caller has a real (e.g. Maps) ETA,
                pass it here instead of using the profile default.
            personal_buffer_min: optional override of the 15-minute personal pad.
        """
        if depart_local.tzinfo is None:
            raise ValueError("depart_local must be timezone-aware")

        profile = AIRPORT_PROFILES.get(origin_iata.upper(), GENERIC_PROFILE)
        category = _categorize_flight(destination_iata)
        peak = _is_peak(depart_local)

        check_in_min = (
            profile.check_in_close_long_haul_min
            if category == FlightCategory.LONG_HAUL
            else profile.check_in_close_short_haul_min
        )
        security_min = profile.security_peak_min if peak else profile.security_offpeak_min
        transfer_min = profile.transfer_to_gate_min

        travel_min = (
            travel_time_override_min
            if travel_time_override_min is not None
            else profile.default_travel_time_min.get(mode, 45)
        )
        personal_min = (
            personal_buffer_min
            if personal_buffer_min is not None
            else self.DEFAULT_PERSONAL_BUFFER_MIN
        )

        breakdown = AirportAdviceBreakdown(
            flight_category=category,
            mode=mode,
            is_peak=peak,
            check_in_close_min=check_in_min,
            security_min=security_min,
            transfer_to_gate_min=transfer_min,
            travel_time_min=travel_min,
            personal_buffer_min=personal_min,
        )
        leave_by = depart_local - timedelta(minutes=breakdown.total_offset_min)

        confidence = "estimate" if travel_time_override_min is None else "live"
        sources = ["airport_profile"]
        if travel_time_override_min is not None:
            sources.append("travel_time_override")

        notes: list[str] = []
        if profile is GENERIC_PROFILE:
            notes.append(
                f"No profile for {origin_iata.upper()} — using generic buffers."
            )
        if travel_time_override_min is None:
            notes.append(
                "Travel time is a static estimate, not traffic-aware. "
                "Add Google Maps integration for live ETA."
            )
        if category == FlightCategory.LONG_HAUL:
            notes.append("Treated as long-haul — extra check-in lead time applied.")

        return AirportAdvice(
            leave_by_local=leave_by,
            depart_local=depart_local,
            origin_iata=origin_iata.upper(),
            destination_iata=destination_iata.upper(),
            breakdown=breakdown,
            confidence=confidence,
            data_sources=sources,
            notes=notes,
        )
