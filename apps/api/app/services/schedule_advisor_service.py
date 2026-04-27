"""
Schedule Advisor Service

Cross-cutting orchestration layer that coordinates:
- Location awareness (Home Assistant presence)
- Calendar events (Google Calendar)
- Transit intelligence (TFI GTFS-R)

Provides proactive "when to leave" recommendations based on current location,
next calendar event, and real-time transit departures.
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from app.services.home_assistant_service import HomeAssistantService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.transit_service import TransitService
import re


class ScheduleAdvisorService:
    """Orchestrates location + calendar + transit to advise when to leave."""
    
    def __init__(self):
        self.ha_service = HomeAssistantService()
        self.calendar_service = GoogleCalendarService()
        self.transit_service = TransitService()
        
        # Known location → transit stop mappings
        self.location_stops = {
            "home": {
                "name": "Coolock",
                "bus_stops": ["4513"],  # Tonlegee Rd
                "modes": ["bus", "dart"]
            },
            "work": {
                "name": "Harcourt St",
                "bus_stops": ["3666"],  # Harcourt St
                "luas_stops": ["HAR"],
                "modes": ["luas", "bus"]
            }
        }
        
        # Known destination → transit stop mappings
        self.destination_stops = {
            "harcourt": {
                "name": "Harcourt St",
                "bus_stops": ["3666"],
                "luas_stops": ["HAR"],
                "routes": ["15", "15A", "15B"]
            },
            "coolock": {
                "name": "Coolock",
                "bus_stops": ["4513"],
                "routes": ["27", "27A", "15"]
            },
            "dalkey": {
                "name": "Dalkey",
                "dart_stations": ["DLKEY"],
                "modes": ["dart"]
            },
            "city centre": {
                "name": "City Centre",
                "bus_stops": ["7602"],  # O'Connell St
                "luas_stops": ["OCC"],
                "routes": ["various"]
            }
        }
    
    def get_next_departure_advice(
        self,
        person_id: str = "declan",
        lookahead_hours: int = 4
    ) -> Dict:
        """
        Main orchestration method: analyzes current location, next calendar event,
        and real-time transit to recommend when to leave.
        
        Returns approval-card shaped advice:
        {
            "advice": "Leave at 13:42 to catch the 15A",
            "current_location": "home",
            "next_event": {...},
            "transit_options": [...],
            "recommended_departure": "2026-04-25T13:42:00",
            "status": "on_time" | "tight" | "urgent" | "missed"
        }
        """
        
        # 1. Get current location
        try:
            location_state = self.ha_service.get_person_state(person_id)
            current_location = location_state.get("state", "unknown")
            location_zone = self._normalize_zone(current_location)
        except Exception as e:
            print(f"Warning: Could not fetch location from HA: {e}")
            current_location = "unknown"
            location_zone = None
        
        # 2. Get next calendar event
        try:
            now = datetime.now(timezone.utc)
            time_min = now.isoformat()
            time_max = (now + timedelta(hours=lookahead_hours)).isoformat()
            
            events = self.calendar_service.list_upcoming_events(
                calendar_id="primary",
                max_results=5
            )
            
            if not events or len(events) == 0:
                return {
                    "advice": "No upcoming events in the next 4 hours. Relax! 😎",
                    "current_location": current_location,
                    "next_event": None,
                    "transit_options": [],
                    "status": "relaxed"
                }
            
            next_event = events[0]
            
        except Exception as e:
            print(f"Warning: Could not fetch calendar events: {e}")
            return {
                "advice": "Could not access calendar",
                "current_location": current_location,
                "error": str(e),
                "status": "error"
            }
        
        # 3. Parse event for location and time
        event_location = next_event.get("location", "")
        event_summary = next_event.get("summary", "Untitled Event")
        
        # Extract start time
        start = next_event.get("start", {})
        if "dateTime" in start:
            event_start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        elif "date" in start:
            # All-day event
            return {
                "advice": f"Next: {event_summary} (all-day event)",
                "current_location": current_location,
                "next_event": next_event,
                "status": "all_day"
            }
        else:
            return {
                "advice": "Next event has no valid time",
                "current_location": current_location,
                "next_event": next_event,
                "status": "error"
            }
        
        # 4. Determine destination zone
        destination_zone = self._infer_destination_zone(event_location, event_summary)
        
        if not location_zone or not destination_zone:
            # Can't determine origin or destination
            minutes_until = int((event_start_dt - now).total_seconds() / 60)
            return {
                "advice": f"Next: {event_summary} in {minutes_until} min. Location unknown — check manually.",
                "current_location": current_location,
                "next_event": next_event,
                "event_location": event_location,
                "status": "unknown_location"
            }
        
        # 5. Get transit options
        transit_options = self._get_transit_options(
            origin_zone=location_zone,
            destination_zone=destination_zone,
            arrival_time=event_start_dt
        )
        
        if not transit_options:
            minutes_until = int((event_start_dt - now).total_seconds() / 60)
            return {
                "advice": f"No transit found from {location_zone} → {destination_zone}. {minutes_until} min until event.",
                "current_location": current_location,
                "next_event": next_event,
                "status": "no_transit"
            }
        
        # 6. Calculate recommended departure
        best_option = transit_options[0]
        recommended_departure_dt = best_option["leave_at_dt"]
        minutes_until_depart = int((recommended_departure_dt - now).total_seconds() / 60)
        
        # 7. Determine urgency status
        if minutes_until_depart < 0:
            status = "missed"
            advice = f"⚠️ You needed to leave {abs(minutes_until_depart)} min ago for {event_summary}"
        elif minutes_until_depart <= 5:
            status = "urgent"
            advice = f"🚨 LEAVE NOW for {event_summary}! Catch the {best_option['route']} in {minutes_until_depart} min"
        elif minutes_until_depart <= 15:
            status = "tight"
            advice = f"⏰ Leave in {minutes_until_depart} min to catch the {best_option['route']} at {best_option['departure_time']}"
        else:
            status = "on_time"
            leave_at_str = recommended_departure_dt.strftime("%H:%M")
            advice = f"Leave at {leave_at_str} to catch the {best_option['route']} ({minutes_until_depart} min)"
        
        return {
            "advice": advice,
            "current_location": current_location,
            "location_zone": location_zone,
            "destination_zone": destination_zone,
            "next_event": {
                "summary": event_summary,
                "location": event_location,
                "start": event_start_dt.isoformat(),
                "id": next_event.get("id")
            },
            "transit_options": transit_options[:3],  # Top 3 options
            "recommended_departure": recommended_departure_dt.isoformat(),
            "minutes_until_depart": minutes_until_depart,
            "status": status
        }
    
    def _normalize_zone(self, ha_state: str) -> Optional[str]:
        """Normalize Home Assistant zone state to our known zones."""
        state_lower = ha_state.lower().strip()
        if state_lower in ["home", "house"]:
            return "home"
        elif state_lower in ["work", "office", "harcourt"]:
            return "work"
        else:
            return None
    
    def _infer_destination_zone(self, location_str: str, summary_str: str) -> Optional[str]:
        """Infer destination zone from calendar event location or summary."""
        combined = f"{location_str} {summary_str}".lower()
        
        if any(kw in combined for kw in ["harcourt", "work", "office"]):
            return "harcourt"
        elif any(kw in combined for kw in ["coolock", "home", "house"]):
            return "coolock"
        elif any(kw in combined for kw in ["dalkey", "dart"]):
            return "dalkey"
        elif any(kw in combined for kw in ["city centre", "o'connell", "temple bar"]):
            return "city centre"
        else:
            return None
    
    def _get_transit_options(
        self,
        origin_zone: str,
        destination_zone: str,
        arrival_time: datetime,
        buffer_minutes: int = 10
    ) -> List[Dict]:
        """
        Get real-time transit options from origin → destination that arrive before arrival_time.
        
        Returns sorted list of options (earliest departure first):
        [
            {
                "route": "15A",
                "mode": "bus",
                "departure_time": "13:42",
                "arrival_time": "14:18",
                "leave_at_dt": datetime,
                "travel_minutes": 36,
                "buffer_ok": True
            }
        ]
        """
        
        # Get origin stop IDs
        origin_config = self.location_stops.get(origin_zone)
        if not origin_config:
            return []
        
        # Get destination config
        dest_config = self.destination_stops.get(destination_zone)
        if not dest_config:
            return []
        
        options = []
        
        # Query bus departures from origin stops
        if "bus_stops" in origin_config:
            for stop_id in origin_config["bus_stops"]:
                try:
                    # If we know destination routes, filter
                    route_filter = dest_config.get("routes", [None])[0] if "routes" in dest_config else None
                    
                    departures_data = self.transit_service.get_bus_departures(
                        stop_id=stop_id,
                        route_short_name=route_filter
                    )
                    
                    departures = departures_data.get("departures", [])
                    
                    for dep in departures:
                        # Estimate arrival time (for now, use fixed travel times)
                        # TODO: Use Google Maps API or TFI journey planner for accurate travel time
                        travel_minutes = self._estimate_travel_time(origin_zone, destination_zone)
                        
                        due = dep["due_minutes"]
                        if due == "Due":
                            departure_minutes = 0
                        else:
                            departure_minutes = int(due)
                        
                        now = datetime.now(timezone.utc)
                        departure_dt = now + timedelta(minutes=departure_minutes)
                        estimated_arrival_dt = departure_dt + timedelta(minutes=travel_minutes)
                        
                        # Check if arrival is before event start (with buffer)
                        if estimated_arrival_dt <= (arrival_time - timedelta(minutes=buffer_minutes)):
                            leave_at_dt = departure_dt - timedelta(minutes=5)  # 5 min walk to stop
                            
                            options.append({
                                "route": dep["route"],
                                "mode": "bus",
                                "destination": dep["destination"],
                                "departure_time": departure_dt.strftime("%H:%M"),
                                "arrival_time": estimated_arrival_dt.strftime("%H:%M"),
                                "leave_at_dt": leave_at_dt,
                                "travel_minutes": travel_minutes,
                                "buffer_ok": True,
                                "due_minutes": departure_minutes
                            })
                
                except Exception as e:
                    print(f"Error fetching bus departures for stop {stop_id}: {e}")
                    continue
        
        # Sort by leave_at_dt (earliest first)
        options.sort(key=lambda x: x["leave_at_dt"])
        
        return options
    
    def _estimate_travel_time(self, origin_zone: str, destination_zone: str) -> int:
        """
        Estimate travel time in minutes between known zones.
        TODO: Replace with Google Maps API or TFI journey planner.
        """
        travel_times = {
            ("home", "harcourt"): 35,
            ("home", "work"): 35,
            ("work", "home"): 35,
            ("harcourt", "coolock"): 35,
            ("home", "city centre"): 25,
            ("work", "dalkey"): 45,
        }
        
        key = (origin_zone, destination_zone)
        return travel_times.get(key, 30)  # Default 30 min


def main():
    """CLI test for schedule advisor."""
    service = ScheduleAdvisorService()
    
    print("=" * 60)
    print("Schedule Advisor Service — Test Run")
    print("=" * 60)
    
    advice = service.get_next_departure_advice(person_id="declan")
    
    print(f"\n📍 Current Location: {advice.get('current_location')}")
    print(f"💡 Advice: {advice.get('advice')}")
    print(f"🚦 Status: {advice.get('status')}")
    
    if advice.get("next_event"):
        event = advice["next_event"]
        print(f"\n📅 Next Event: {event.get('summary')}")
        print(f"   Location: {event.get('location')}")
        print(f"   Start: {event.get('start')}")
    
    if advice.get("transit_options"):
        print(f"\n🚌 Transit Options:")
        for i, opt in enumerate(advice["transit_options"][:3], 1):
            print(f"   {i}. {opt['route']} — Depart {opt['departure_time']}, Arrive {opt['arrival_time']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
