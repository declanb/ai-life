"""One-time Spotify OAuth bootstrap using PKCE flow.

Run once:
    cd apps/api && python -m app.cli.spotify_auth

Opens a browser for Spotify consent, exchanges the auth code on a loopback redirect,
and writes the access + refresh tokens to apps/api/.secrets/spotify_oauth_token.json.
"""
from __future__ import annotations

import json
import sys
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.core.settings import get_settings
from app.services.spotify_service import SpotifyService


# Global to capture the authorization code from the callback
_auth_code: Optional[str] = None
_auth_state: Optional[str] = None
_code_verifier: Optional[str] = None


class CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth callback from Spotify."""
    
    def do_GET(self):
        global _auth_code, _auth_state
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        _auth_code = params.get("code", [None])[0]
        _auth_state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]
        
        if error:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<h1>Authorization Failed</h1><p>Error: {error}</p>".encode()
            )
        elif _auth_code:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization Successful!</h1>"
                b"<p>You can close this window and return to the terminal.</p>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization Failed</h1>"
                b"<p>No authorization code received.</p>"
            )
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs to keep output clean."""
        pass


def start_local_server(port: int) -> HTTPServer:
    """Start a local HTTP server for the OAuth callback."""
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server


def main() -> int:
    global _auth_code, _auth_state, _code_verifier
    
    settings = get_settings()
    client_file = settings.spotify_oauth_client_file
    token_file = settings.spotify_oauth_token_file

    if not client_file.exists():
        print(f"❌ Missing Spotify client config at {client_file}", file=sys.stderr)
        print("\nCreate this file with your Spotify app credentials:", file=sys.stderr)
        print(json.dumps({
            "client_id": "YOUR_CLIENT_ID_FROM_SPOTIFY_DASHBOARD",
            "redirect_uri": "http://127.0.0.1:8765"
        }, indent=2), file=sys.stderr)
        print("\nGet credentials from: https://developer.spotify.com/dashboard", file=sys.stderr)
        return 1

    # Load client config
    client_config = json.loads(client_file.read_text())
    client_id = client_config.get("client_id")
    redirect_uri = client_config.get("redirect_uri", f"http://127.0.0.1:{settings.oauth_loopback_port}")
    
    if not client_id:
        print("❌ client_id missing from Spotify client config", file=sys.stderr)
        return 1

    # Generate PKCE challenge
    _code_verifier = SpotifyService.generate_code_verifier()
    code_challenge = SpotifyService.generate_code_challenge(_code_verifier)
    
    # Generate state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(16)
    
    # Build authorization URL
    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(settings.spotify_oauth_scopes),
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
    }
    
    auth_url = f"{SpotifyService.AUTH_BASE}/authorize?{urlencode(auth_params)}"
    
    # Start local server
    port = int(redirect_uri.split(":")[-1]) if ":" in redirect_uri else settings.oauth_loopback_port
    print(f"🎵 Starting local server on port {port}...")
    server = start_local_server(port)
    
    # Open browser
    print(f"🌐 Opening browser for Spotify authorization...")
    print(f"    If it doesn't open automatically, visit:\n    {auth_url}\n")
    webbrowser.open(auth_url)
    
    # Wait for callback
    print("⏳ Waiting for authorization...")
    server.server_close()  # Wait until the single request is handled
    
    if not _auth_code:
        print("❌ No authorization code received", file=sys.stderr)
        return 1
    
    if _auth_state != state:
        print("❌ State mismatch - possible CSRF attack", file=sys.stderr)
        return 1
    
    print("✅ Authorization code received, exchanging for tokens...")
    
    # Exchange code for tokens
    token_payload = {
        "grant_type": "authorization_code",
        "code": _auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": _code_verifier,
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{SpotifyService.AUTH_BASE}/api/token",
                data=token_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
    except Exception as exc:
        print(f"❌ Token exchange failed: {exc}", file=sys.stderr)
        return 1
    
    # Calculate token expiry
    expires_at = (
        datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
    ).isoformat()
    
    # Prepare token file
    token_payload = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at": expires_at,
        "scope": token_data.get("scope", ""),
    }
    
    # Save token
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(json.dumps(token_payload, indent=2))
    print(f"✅ Saved credentials to {token_file}")
    
    # Test the token
    print("\n🧪 Testing API access...")
    try:
        spotify = SpotifyService(settings)
        user = spotify.get_current_user()
        print(f"✅ Authenticated as: {user['display_name']} ({user['email']})")
        print(f"   Account type: {user['product']}")
        
        devices = spotify.get_available_devices()
        if devices:
            print(f"   Available devices: {', '.join(d['name'] for d in devices)}")
        else:
            print("   No active Spotify devices found (start Spotify on a device to see it here)")
    except Exception as exc:
        print(f"⚠️  API test failed: {exc}", file=sys.stderr)
        print("   Token saved successfully, but API call failed. This is usually OK.", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
