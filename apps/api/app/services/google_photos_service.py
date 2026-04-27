"""Wraps Google Photos Library API for upload-only mirroring.

Uses the Library API to:
  - Create an app-owned "iCloud Mirror" album
  - Upload photos into the user's library
  - Append uploaded photos to the mirror album
  - List app-created items for idempotency checks

OAuth: reuses the token bootstrapped by `python -m app.cli.google_auth`.

Scopes (see settings.google_oauth_scopes):
  - https://www.googleapis.com/auth/photoslibrary.appendonly
  - https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata

Library API reference:
  - https://developers.google.com/photos/library/reference/rest
  - https://developers.google.com/photos/library/guides/upload-media

Note: the Library API has no discovery doc, so we call it via httpx rather
than googleapiclient.discovery.build(...).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import google.auth
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.settings import Settings, get_settings
from app.schemas.photo import Album, Photo, Upload


PHOTOS_API_BASE = "https://photoslibrary.googleapis.com/v1"
MIRROR_ALBUM_TITLE = "AI-Life — iCloud Mirror"


class GooglePhotosService:
    """Google Photos Library API client for the iCloud → Google Photos mirror.

    Capability (post-March 2025, verified April 2026):
      ✓ Upload new photos (two-step /v1/uploads → mediaItems.batchCreate)
      ✓ Create app-owned albums
      ✓ Append photos to app-owned albums
      ✓ List app-created albums and media items
      ✗ Delete media items (no API support anywhere)
      ✗ Read user's full library (restricted to app-created content)
      ✗ Manage shared albums (scope removed)
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._creds: Any = None

    # --- auth -----------------------------------------------------------------
    def _load_credentials(self) -> Credentials:
        """Load credentials, preferring the local OAuth token file.

        Mirrors google_calendar_service._load_credentials. Falls back to ADC.
        """
        token_path: Path = self.settings.google_oauth_token_file
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), self.settings.google_oauth_scopes
            )
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    token_path.write_text(creds.to_json())
                else:
                    raise RuntimeError(
                        "Stored Google credentials are invalid and cannot be refreshed. "
                        "Re-run `python -m app.cli.google_auth`."
                    )
            return creds

        try:
            creds, _ = google.auth.default(scopes=self.settings.google_oauth_scopes)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "No Google credentials available. Run `python -m app.cli.google_auth`."
            ) from exc
        return creds

    def _auth_header(self) -> dict[str, str]:
        if self._creds is None or not getattr(self._creds, "valid", False):
            self._creds = self._load_credentials()
        return {"Authorization": f"Bearer {self._creds.token}"}

    # --- verification ---------------------------------------------------------
    def verify_access(self) -> dict[str, Any]:
        """Confirm the current token can talk to the Photos Library API.

        Calls `GET /v1/albums?pageSize=1` which requires
        photoslibrary.readonly.appcreateddata. Raises on auth failure.
        """
        resp = httpx.get(
            f"{PHOTOS_API_BASE}/albums",
            params={"pageSize": 1, "excludeNonAppCreatedData": "true"},
            headers=self._auth_header(),
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "ok": True,
            "app_created_albums_visible": len(body.get("albums", [])),
            "has_next_page": bool(body.get("nextPageToken")),
        }

    # --- albums ---------------------------------------------------------------
    def ensure_mirror_album(self) -> Album:
        """Find or create the app-owned mirror album. Idempotent."""
        with httpx.Client(timeout=15.0, headers=self._auth_header()) as client:
            page_token: Optional[str] = None
            while True:
                params: dict[str, Any] = {
                    "pageSize": 50,
                    "excludeNonAppCreatedData": "true",
                }
                if page_token:
                    params["pageToken"] = page_token
                r = client.get(f"{PHOTOS_API_BASE}/albums", params=params)
                r.raise_for_status()
                body = r.json()
                for alb in body.get("albums", []):
                    if alb.get("title") == MIRROR_ALBUM_TITLE:
                        return Album(
                            google_album_id=alb["id"],
                            title=alb["title"],
                            app_created=True,
                        )
                page_token = body.get("nextPageToken")
                if not page_token:
                    break

            r = client.post(
                f"{PHOTOS_API_BASE}/albums",
                json={"album": {"title": MIRROR_ALBUM_TITLE}},
            )
            r.raise_for_status()
            alb = r.json()
            return Album(
                google_album_id=alb["id"],
                title=alb["title"],
                app_created=True,
            )

    # --- upload (not yet implemented) -----------------------------------------
    def upload_media(self, photo: Photo, file_path: Path) -> Upload:
        """Upload a photo to Google Photos (two-step: /v1/uploads → batchCreate).

        TODO: implement in the next slice. Stub preserved so the orchestrator
        can wire through dry-run paths today.
        """
        raise NotImplementedError(
            "upload_media is not implemented yet. See next-slice plan."
        )

    def list_app_created_items(self) -> list[Upload]:
        """List all media items this app has uploaded.

        TODO: implement via mediaItems.list (paginated). Stub for now.
        """
        return []
