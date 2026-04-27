"""Pydantic schemas for the photos mirror feature.

Matches the SQLite schema design for iCloud → Google Photos sync state.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class PhotoState(str, Enum):
    """State machine for photo sync lifecycle."""
    DISCOVERED = "discovered"
    EXPORTED = "exported"
    HASHED = "hashed"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    FAILED_EXPORT = "failed_export"
    FAILED_HASH = "failed_hash"
    FAILED_UPLOAD = "failed_upload"


class Photo(BaseModel):
    """A photo discovered from iCloud Photos (via osxphotos export).
    
    Tracks both the original metadata from iCloud and computed hashes for dedupe.
    """
    icloud_uuid: str = Field(..., description="iCloud photo UUID (from Photos.app)")
    original_filename: str
    capture_time: datetime
    sha256: Optional[str] = Field(None, description="SHA-256 of exported original file")
    perceptual_hash: Optional[str] = Field(None, description="Perceptual hash (for fuzzy dedupe)")
    live_photo_pair_uuid: Optional[str] = Field(None, description="UUID of paired Live Photo video component")
    exif_gps_redacted: bool = Field(False, description="True if GPS was stripped for privacy")
    state: PhotoState = PhotoState.DISCOVERED
    error_message: Optional[str] = None


class ExportRun(BaseModel):
    """Metadata for an osxphotos export run."""
    run_id: str  # auto-generated UUID
    started_at: datetime
    finished_at: Optional[datetime] = None
    exit_status: Optional[int] = None
    exported_count: int = 0


class Upload(BaseModel):
    """Upload record linking a Photo to its Google Photos MediaItem."""
    photo_uuid: str  # FK to Photo.icloud_uuid
    google_media_item_id: Optional[str] = Field(None, description="Google Photos MediaItem ID after upload")
    google_album_id: Optional[str] = Field(None, description="Album the item was added to")
    uploaded_at: Optional[datetime] = None
    bytes: Optional[int] = None
    status: str = "pending"  # pending, uploading, uploaded, failed


class Album(BaseModel):
    """Google Photos album metadata."""
    google_album_id: str
    title: str
    app_created: bool = Field(True, description="True if created by this app (vs. user-owned)")


class SyncStatus(BaseModel):
    """Overall sync status returned by run_sync."""
    last_export_run_id: Optional[str] = None
    total_photos_discovered: int = 0
    total_photos_exported: int = 0
    total_photos_uploaded: int = 0
    pending_uploads: int = 0
    failed_photos: int = 0
    last_sync_at: Optional[datetime] = None
