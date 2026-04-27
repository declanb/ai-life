"""Spotify service for AI-Life Physical Layer.

Responsibilities:
- OAuth 2.0 with PKCE for user authorization
- Read current playback state (track, device, shuffle, volume)
- Control playback (play/pause/skip/volume/shuffle)
- Access user's playlists for context-aware music selection
- Provide foundation for Home Assistant integration later
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx

from app.core.settings import Settings, get_settings


class SpotifyService:
    """Client for Spotify Web API using Authorization Code with PKCE flow."""
    
    API_BASE = "https://api.spotify.com/v1"
    AUTH_BASE = "https://accounts.spotify.com"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._token_data: Optional[dict] = None
        self._client_config: Optional[dict] = None

    # --- OAuth / Credentials --------------------------------------------------
    
    def _load_client_config(self) -> dict:
        """Load Spotify app client ID and redirect URI from secrets."""
        if self._client_config is None:
            client_file = self.settings.spotify_oauth_client_file
            if not client_file.exists():
                raise FileNotFoundError(
                    f"Spotify client config not found at {client_file}. "
                    f"Create it with: {{'client_id': 'YOUR_CLIENT_ID', 'redirect_uri': 'http://127.0.0.1:8765'}}"
                )
            self._client_config = json.loads(client_file.read_text())
        return self._client_config

    def _load_token(self) -> dict:
        """Load stored OAuth token, refreshing if expired."""
        if self._token_data is not None:
            return self._token_data

        token_file = self.settings.spotify_oauth_token_file
        if not token_file.exists():
            raise FileNotFoundError(
                f"Spotify OAuth token not found at {token_file}. "
                f"Run: python -m app.cli.spotify_auth"
            )

        self._token_data = json.loads(token_file.read_text())
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(self._token_data.get("expires_at", "1970-01-01T00:00:00"))
        if datetime.now() >= expires_at:
            self._refresh_token()
        
        return self._token_data

    def _refresh_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if self._token_data is None or "refresh_token" not in self._token_data:
            raise RuntimeError("No refresh token available. Re-run: python -m app.cli.spotify_auth")

        client_config = self._load_client_config()
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._token_data["refresh_token"],
            "client_id": client_config["client_id"],
        }

        with httpx.Client() as client:
            response = client.post(
                f"{self.AUTH_BASE}/api/token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_resp = response.json()

        # Update token data
        self._token_data["access_token"] = token_resp["access_token"]
        self._token_data["expires_at"] = (
            datetime.now() + timedelta(seconds=token_resp["expires_in"])
        ).isoformat()
        
        # Preserve refresh_token if not included in response (some flows don't return it)
        if "refresh_token" in token_resp:
            self._token_data["refresh_token"] = token_resp["refresh_token"]

        # Persist updated token
        self.settings.spotify_oauth_token_file.write_text(
            json.dumps(self._token_data, indent=2)
        )

    @property
    def _auth_headers(self) -> dict[str, str]:
        """Build Authorization header with current access token."""
        token = self._load_token()
        return {"Authorization": f"Bearer {token['access_token']}"}

    # --- Playback State (Read) ------------------------------------------------

    def get_current_playback(self) -> Optional[dict]:
        """Get the user's current playback state.
        
        Returns None if nothing is playing, otherwise dict with:
        - is_playing (bool)
        - track (dict): name, artist, album, uri
        - device (dict): name, type, volume_percent
        - shuffle_state (bool)
        - repeat_state (str): "off", "track", "context"
        - progress_ms (int)
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.API_BASE}/me/player",
                headers=self._auth_headers,
            )
            
            if response.status_code == 204:  # No content = nothing playing
                return None
            
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            # Extract key fields
            item = data.get("item") or {}
            device = data.get("device") or {}
            
            return {
                "is_playing": data.get("is_playing", False),
                "track": {
                    "name": item.get("name", "Unknown"),
                    "artist": ", ".join(a["name"] for a in item.get("artists", [])),
                    "album": item.get("album", {}).get("name", "Unknown"),
                    "uri": item.get("uri", ""),
                    "duration_ms": item.get("duration_ms", 0),
                },
                "device": {
                    "name": device.get("name", "Unknown"),
                    "type": device.get("type", "Unknown"),
                    "volume_percent": device.get("volume_percent", 0),
                    "id": device.get("id", ""),
                },
                "shuffle_state": data.get("shuffle_state", False),
                "repeat_state": data.get("repeat_state", "off"),
                "progress_ms": data.get("progress_ms", 0),
            }

    def get_available_devices(self) -> list[dict]:
        """List available Spotify Connect devices.
        
        Returns list of dicts with: id, name, type, is_active, volume_percent
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.API_BASE}/me/player/devices",
                headers=self._auth_headers,
            )
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "is_active": d.get("is_active", False),
                    "volume_percent": d.get("volume_percent", 0),
                }
                for d in data.get("devices", [])
            ]

    # --- Playback Control (Write) ---------------------------------------------

    def play(
        self,
        device_id: Optional[str] = None,
        context_uri: Optional[str] = None,
        uris: Optional[list[str]] = None,
    ) -> None:
        """Start or resume playback.
        
        Args:
            device_id: Target device ID. If None, uses currently active device.
            context_uri: Spotify URI of album, artist, or playlist (e.g. "spotify:playlist:...")
            uris: List of track URIs to play (e.g. ["spotify:track:..."])
        """
        params = {"device_id": device_id} if device_id else {}
        body = {}
        
        if context_uri:
            body["context_uri"] = context_uri
        if uris:
            body["uris"] = uris

        with httpx.Client() as client:
            response = client.put(
                f"{self.API_BASE}/me/player/play",
                headers=self._auth_headers,
                params=params,
                json=body if body else None,
            )
            response.raise_for_status()

    def pause(self, device_id: Optional[str] = None) -> None:
        """Pause playback."""
        params = {"device_id": device_id} if device_id else {}
        
        with httpx.Client() as client:
            response = client.put(
                f"{self.API_BASE}/me/player/pause",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    def skip_to_next(self, device_id: Optional[str] = None) -> None:
        """Skip to next track."""
        params = {"device_id": device_id} if device_id else {}
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.API_BASE}/me/player/next",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    def skip_to_previous(self, device_id: Optional[str] = None) -> None:
        """Skip to previous track."""
        params = {"device_id": device_id} if device_id else {}
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.API_BASE}/me/player/previous",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> None:
        """Set playback volume (0-100)."""
        if not 0 <= volume_percent <= 100:
            raise ValueError("Volume must be between 0 and 100")
        
        params = {"volume_percent": volume_percent}
        if device_id:
            params["device_id"] = device_id

        with httpx.Client() as client:
            response = client.put(
                f"{self.API_BASE}/me/player/volume",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> None:
        """Enable or disable shuffle."""
        params = {"state": str(state).lower()}
        if device_id:
            params["device_id"] = device_id

        with httpx.Client() as client:
            response = client.put(
                f"{self.API_BASE}/me/player/shuffle",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    def set_repeat(self, state: str, device_id: Optional[str] = None) -> None:
        """Set repeat mode: 'track', 'context', or 'off'."""
        if state not in ["track", "context", "off"]:
            raise ValueError("Repeat state must be 'track', 'context', or 'off'")
        
        params = {"state": state}
        if device_id:
            params["device_id"] = device_id

        with httpx.Client() as client:
            response = client.put(
                f"{self.API_BASE}/me/player/repeat",
                headers=self._auth_headers,
                params=params,
            )
            response.raise_for_status()

    # --- Playlists ------------------------------------------------------------

    def get_user_playlists(self, limit: int = 20) -> list[dict]:
        """Get user's playlists.
        
        Returns list of dicts with: id, name, uri, tracks_total, public
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.API_BASE}/me/playlists",
                headers=self._auth_headers,
                params={"limit": limit},
            )
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "uri": p["uri"],
                    "tracks_total": p["tracks"]["total"],
                    "public": p.get("public", False),
                }
                for p in data.get("items", [])
            ]

    # --- User Profile ---------------------------------------------------------

    def get_current_user(self) -> dict:
        """Get current user profile.
        
        Returns dict with: id, display_name, email, product (account type)
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.API_BASE}/me",
                headers=self._auth_headers,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "id": data["id"],
                "display_name": data.get("display_name", "Unknown"),
                "email": data.get("email", ""),
                "product": data.get("product", "free"),  # "premium" or "free"
            }

    # --- Static PKCE Helpers (for CLI auth) -----------------------------------

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate PKCE code verifier (43-128 random chars)."""
        return base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("utf-8").rstrip("=")

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Generate PKCE code challenge from verifier (SHA256 + base64)."""
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
