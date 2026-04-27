"""Home Assistant service for AI-Life.

Responsibilities:
- Connect to local Home Assistant instance via REST API
- Read entity states (presence sensors, person entities, etc.)
- Provide presence/location data for context-aware orchestration

Authentication:
- Long-lived access token (user-generated in HA UI)
- Stored in .secrets/home_assistant_token.txt
- Local network only by default (http://homeassistant.local:8123)

Security:
- Read-only operations for now
- No state changes without approval-card gate
- Token never logged or sent to LLM
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.core.settings import Settings, get_settings


logger = logging.getLogger(__name__)


class HomeAssistantService:
    """Client for Home Assistant REST API.
    
    Provides read-only access to entity states, focusing on presence/location
    data for orchestration features (e.g., "when to leave" calculations).
    
    Usage:
        >>> service = HomeAssistantService()
        >>> person_state = service.get_person_state("declan")
        >>> print(person_state["state"])  # "home", "work", "not_home", etc.
    """
    
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """Lazy-init HTTP client with auth header."""
        if self._client is None:
            base_url = self.settings.home_assistant_url
            token = self._load_token()
            
            if not base_url or not token:
                raise RuntimeError(
                    "Home Assistant not configured. Set HOME_ASSISTANT_URL and "
                    "store token in .secrets/home_assistant_token.txt"
                )
            
            self._client = httpx.Client(
                base_url=base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        return self._client
    
    def _load_token(self) -> Optional[str]:
        """Load long-lived access token from .secrets directory.
        
        Token file should contain just the token string, no extra whitespace.
        Generate in Home Assistant UI: Profile → Long-Lived Access Tokens
        """
        token_file = self.settings.home_assistant_token_file
        if not token_file.exists():
            logger.warning(
                f"Home Assistant token file not found: {token_file}. "
                "Generate a long-lived access token in HA UI and save to this file."
            )
            return None
        
        token = token_file.read_text().strip()
        if not token:
            logger.warning(f"Home Assistant token file is empty: {token_file}")
            return None
        
        return token
    
    def check_connection(self) -> Dict[str, Any]:
        """Test connection to Home Assistant.
        
        Returns:
            Dict with 'status' ("ok" or "error"), 'version', 'message'.
        """
        try:
            response = self.client.get("/api/")
            response.raise_for_status()
            data = response.json()
            return {
                "status": "ok",
                "message": data.get("message", "API running"),
                "version": None,  # Basic endpoint doesn't return version
            }
        except httpx.HTTPStatusError as exc:
            logger.error(f"Home Assistant HTTP error: {exc.response.status_code}")
            return {
                "status": "error",
                "message": f"HTTP {exc.response.status_code}: {exc.response.text}",
            }
        except httpx.RequestError as exc:
            logger.error(f"Home Assistant connection error: {exc}")
            return {
                "status": "error",
                "message": f"Connection failed: {exc}",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error checking Home Assistant: {exc}")
            return {
                "status": "error",
                "message": f"Unexpected error: {exc}",
            }
    
    def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of any Home Assistant entity.
        
        Args:
            entity_id: Full entity ID, e.g. "person.declan", "sensor.living_room_temperature"
        
        Returns:
            Dict with keys: entity_id, state, attributes, last_changed, last_updated
            None if entity not found or HA unreachable
        
        Example response:
            {
                "entity_id": "person.declan",
                "state": "home",
                "attributes": {
                    "latitude": 53.xxxx,
                    "longitude": -6.xxxx,
                    "source": "device_tracker.iphone",
                    "friendly_name": "Declan"
                },
                "last_changed": "2026-04-25T08:30:00+00:00",
                "last_updated": "2026-04-25T08:30:00+00:00"
            }
        """
        try:
            response = self.client.get(f"/api/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(f"Entity not found: {entity_id}")
            else:
                logger.error(
                    f"Error fetching entity {entity_id}: "
                    f"HTTP {exc.response.status_code}"
                )
            return None
        except httpx.RequestError as exc:
            logger.error(f"Connection error fetching entity {entity_id}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Unexpected error fetching entity {entity_id}: {exc}")
            return None
    
    def get_person_state(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a person entity (presence/location).
        
        Args:
            person_id: Person identifier without 'person.' prefix, e.g. "declan"
        
        Returns:
            Same as get_entity_state, but with person-specific helper fields:
            - state: typically "home", "work", or "not_home" (can also be zone names)
            - location: lat/lng tuple if available
            - source: which device tracker provided this state
        
        Example:
            >>> state = service.get_person_state("declan")
            >>> if state and state["state"] == "home":
            >>>     print("User is home")
        """
        entity_id = f"person.{person_id}"
        state_data = self.get_entity_state(entity_id)
        
        if not state_data:
            return None
        
        # Enhance with convenient accessors
        attrs = state_data.get("attributes", {})
        state_data["location"] = None
        if "latitude" in attrs and "longitude" in attrs:
            state_data["location"] = (attrs["latitude"], attrs["longitude"])
        
        state_data["source"] = attrs.get("source")
        state_data["friendly_name"] = attrs.get("friendly_name", person_id.title())
        
        return state_data
    
    def list_persons(self) -> list[Dict[str, Any]]:
        """List all person entities configured in Home Assistant.
        
        Returns:
            List of person entity states. Empty list if HA unreachable.
        """
        try:
            response = self.client.get("/api/states")
            response.raise_for_status()
            all_states = response.json()
            
            # Filter to person.* entities
            persons = [
                state for state in all_states 
                if state.get("entity_id", "").startswith("person.")
            ]
            return persons
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Error listing persons: {exc}")
            return []
    
    def is_home(self, person_id: str) -> bool:
        """Check if a person is currently home.
        
        Args:
            person_id: Person identifier without 'person.' prefix
        
        Returns:
            True if person state is "home", False otherwise (including errors)
        """
        state = self.get_person_state(person_id)
        if not state:
            logger.warning(
                f"Could not determine home status for {person_id}, "
                "defaulting to False"
            )
            return False
        return state.get("state") == "home"
    
    def get_location_zone(self, person_id: str) -> Optional[str]:
        """Get the current zone/location name for a person.
        
        Args:
            person_id: Person identifier without 'person.' prefix
        
        Returns:
            Zone name ("home", "work", "gym", etc.) or "not_home" if away.
            None if person not found or HA unreachable.
        """
        state = self.get_person_state(person_id)
        if not state:
            return None
        return state.get("state")
    
    def close(self) -> None:
        """Close HTTP client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# --- Usage Examples -----------------------------------------------------------
if __name__ == "__main__":
    # Example 1: Check if user is home
    service = HomeAssistantService()
    
    # Test connection
    conn_status = service.check_connection()
    print(f"Connection status: {conn_status}")
    
    if conn_status["status"] == "ok":
        # Get person state
        person_state = service.get_person_state("declan")
        if person_state:
            print(f"\nPerson: {person_state['friendly_name']}")
            print(f"State: {person_state['state']}")
            print(f"Location: {person_state['location']}")
            print(f"Source: {person_state['source']}")
        
        # Simple boolean check
        if service.is_home("declan"):
            print("\n✓ User is home")
        else:
            print("\n✗ User is away")
        
        # List all persons
        persons = service.list_persons()
        print(f"\nConfigured persons: {len(persons)}")
        for person in persons:
            print(f"  - {person['attributes'].get('friendly_name')}: {person['state']}")
    
    service.close()
