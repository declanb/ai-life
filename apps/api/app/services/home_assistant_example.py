"""Example: Using Home Assistant presence for "when to leave" orchestration.

This demonstrates how the Chief Architect can integrate Home Assistant
presence detection into the departure-time calculation workflow.
"""
from datetime import datetime, timedelta
from app.services.home_assistant_service import HomeAssistantService
from app.services.transit_service import TransitService


def calculate_departure_time(
    person_id: str,
    destination: str,
    arrival_time: datetime,
) -> dict:
    """Calculate when to leave based on current location and transit times.
    
    Args:
        person_id: Person entity ID (e.g., "declan")
        destination: Destination address or zone name
        arrival_time: When you need to arrive
    
    Returns:
        Dict with departure_time, current_location, transit_duration, etc.
    """
    ha_service = HomeAssistantService()
    transit_service = TransitService()
    
    # 1. Determine current location from Home Assistant
    current_zone = ha_service.get_location_zone(person_id)
    
    if not current_zone:
        return {
            "error": "Could not determine current location",
            "person_id": person_id,
            "fallback": "Assume 30 minutes travel time",
        }
    
    # 2. Skip calculation if already at destination
    if current_zone.lower() == destination.lower():
        return {
            "status": "already_at_destination",
            "current_location": current_zone,
            "message": f"You're already at {destination}",
        }
    
    # 3. Calculate transit time from current zone to destination
    # (This is a stub — real implementation would use transit_service
    # to get actual route duration based on current_zone)
    
    if current_zone == "home":
        # Example: Home to work transit lookup
        transit_duration = timedelta(minutes=45)
        buffer = timedelta(minutes=10)  # Buffer for walking, delays
    elif current_zone == "work":
        # Work to home
        transit_duration = timedelta(minutes=40)
        buffer = timedelta(minutes=5)
    else:
        # Unknown zone — use conservative estimate
        transit_duration = timedelta(minutes=30)
        buffer = timedelta(minutes=15)
    
    # 4. Calculate departure time
    total_time_needed = transit_duration + buffer
    departure_time = arrival_time - total_time_needed
    
    # 5. Determine if we need to leave soon
    now = datetime.now()
    time_until_departure = departure_time - now
    
    urgency = "relaxed"
    if time_until_departure < timedelta(minutes=5):
        urgency = "leave_now"
    elif time_until_departure < timedelta(minutes=15):
        urgency = "leave_soon"
    
    return {
        "current_location": current_zone,
        "destination": destination,
        "arrival_time": arrival_time.isoformat(),
        "departure_time": departure_time.isoformat(),
        "transit_duration_minutes": int(transit_duration.total_seconds() / 60),
        "buffer_minutes": int(buffer.total_seconds() / 60),
        "time_until_departure_minutes": int(time_until_departure.total_seconds() / 60),
        "urgency": urgency,
        "person_id": person_id,
    }


def check_presence_for_automation(person_id: str) -> dict:
    """Simple presence check for automation triggers.
    
    Use case: "If user arrives home after 6pm, suggest dinner playlist"
    
    Returns:
        Current presence state with context
    """
    ha_service = HomeAssistantService()
    
    person_state = ha_service.get_person_state(person_id)
    
    if not person_state:
        return {
            "available": False,
            "error": "Home Assistant not available",
        }
    
    return {
        "available": True,
        "person_id": person_id,
        "zone": person_state["state"],
        "is_home": person_state["state"] == "home",
        "location": person_state.get("location"),
        "last_changed": person_state.get("last_changed"),
        "device_source": person_state.get("source"),
    }


if __name__ == "__main__":
    # Example 1: Calculate when to leave for work
    print("=== Departure Time Calculation ===")
    result = calculate_departure_time(
        person_id="declan",
        destination="work",
        arrival_time=datetime.now() + timedelta(hours=1),
    )
    print(f"Current location: {result.get('current_location')}")
    print(f"Departure time: {result.get('departure_time')}")
    print(f"Urgency: {result.get('urgency')}")
    print(f"Transit duration: {result.get('transit_duration_minutes')} minutes")
    
    print("\n=== Presence Check ===")
    # Example 2: Check current presence
    presence = check_presence_for_automation("declan")
    print(f"Is home: {presence.get('is_home')}")
    print(f"Current zone: {presence.get('zone')}")
    print(f"Last changed: {presence.get('last_changed')}")
