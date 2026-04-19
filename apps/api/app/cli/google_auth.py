"""One-time Google OAuth bootstrap.

Run once:
    cd apps/api && python -m app.cli.google_auth

Opens a browser for consent, exchanges the code on a loopback redirect,
and writes the refresh-token-bearing credentials to
apps/api/.secrets/google_oauth_token.json.
"""
from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from app.core.settings import get_settings


def main() -> int:
    settings = get_settings()
    client_file = settings.google_oauth_client_file
    token_file = settings.google_oauth_token_file

    if not client_file.exists():
        print(f"Missing OAuth client JSON at {client_file}", file=sys.stderr)
        print("Download it from Google Cloud Console → Credentials.", file=sys.stderr)
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_file), scopes=settings.google_oauth_scopes
    )
    # Loopback redirect on a fixed port — works for Desktop AND Web-type clients
    # as long as the Web client has http://localhost:<port>/ as an authorised
    # redirect URI.
    creds = flow.run_local_server(port=settings.oauth_loopback_port, prompt="consent")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    print(f"✅ Saved credentials to {token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
