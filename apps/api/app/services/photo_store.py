"""SQLite persistence for photo sync state.

Follows the trip_store.py pattern but uses a proper on-disk SQLite database
(not in-memory) since photo sync state must survive restarts.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from app.schemas.photo import Photo, ExportRun, Upload, Album, PhotoState


# SQLite database location (gitignored; local to Mac running the agent)
DB_PATH = Path(__file__).resolve().parent.parent / ".data" / "photo_sync.db"


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the photo sync database, creating schema if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS photo (
            icloud_uuid TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            capture_time TEXT NOT NULL,
            sha256 TEXT,
            perceptual_hash TEXT,
            live_photo_pair_uuid TEXT,
            exif_gps_redacted INTEGER NOT NULL DEFAULT 0,
            state TEXT NOT NULL DEFAULT 'discovered',
            error_message TEXT
        );
        
        CREATE TABLE IF NOT EXISTS export_run (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            exit_status INTEGER,
            exported_count INTEGER NOT NULL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS upload (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_uuid TEXT NOT NULL,
            google_media_item_id TEXT,
            google_album_id TEXT,
            uploaded_at TEXT,
            bytes INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (photo_uuid) REFERENCES photo(icloud_uuid)
        );
        
        CREATE TABLE IF NOT EXISTS album (
            google_album_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            app_created INTEGER NOT NULL DEFAULT 1
        );
        
        CREATE INDEX IF NOT EXISTS idx_photo_state ON photo(state);
        CREATE INDEX IF NOT EXISTS idx_upload_photo_uuid ON upload(photo_uuid);
        CREATE INDEX IF NOT EXISTS idx_upload_status ON upload(status);
    """)
    conn.commit()


class PhotoStore:
    """Thin SQLite wrapper for photo sync state."""
    
    def upsert_photo(self, photo: Photo) -> None:
        """Insert or update a photo record."""
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO photo (
                    icloud_uuid, original_filename, capture_time, sha256, 
                    perceptual_hash, live_photo_pair_uuid, exif_gps_redacted, state, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(icloud_uuid) DO UPDATE SET
                    original_filename=excluded.original_filename,
                    capture_time=excluded.capture_time,
                    sha256=excluded.sha256,
                    perceptual_hash=excluded.perceptual_hash,
                    live_photo_pair_uuid=excluded.live_photo_pair_uuid,
                    exif_gps_redacted=excluded.exif_gps_redacted,
                    state=excluded.state,
                    error_message=excluded.error_message
                """,
                (
                    photo.icloud_uuid,
                    photo.original_filename,
                    photo.capture_time.isoformat(),
                    photo.sha256,
                    photo.perceptual_hash,
                    photo.live_photo_pair_uuid,
                    int(photo.exif_gps_redacted),
                    photo.state.value,
                    photo.error_message,
                ),
            )
            conn.commit()
    
    def get_photo(self, icloud_uuid: str) -> Optional[Photo]:
        """Retrieve a photo by iCloud UUID."""
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM photo WHERE icloud_uuid = ?", (icloud_uuid,)
            ).fetchone()
            if not row:
                return None
            return Photo(
                icloud_uuid=row["icloud_uuid"],
                original_filename=row["original_filename"],
                capture_time=row["capture_time"],
                sha256=row["sha256"],
                perceptual_hash=row["perceptual_hash"],
                live_photo_pair_uuid=row["live_photo_pair_uuid"],
                exif_gps_redacted=bool(row["exif_gps_redacted"]),
                state=PhotoState(row["state"]),
                error_message=row["error_message"],
            )
    
    def create_export_run(self, run: ExportRun) -> None:
        """Create a new export run record."""
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO export_run (run_id, started_at, finished_at, exit_status, exported_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.exit_status,
                    run.exported_count,
                ),
            )
            conn.commit()
    
    def create_upload(self, upload: Upload) -> None:
        """Create an upload record."""
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO upload (photo_uuid, google_media_item_id, google_album_id, uploaded_at, bytes, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    upload.photo_uuid,
                    upload.google_media_item_id,
                    upload.google_album_id,
                    upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                    upload.bytes,
                    upload.status,
                ),
            )
            conn.commit()
    
    def upsert_album(self, album: Album) -> None:
        """Insert or update an album record."""
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO album (google_album_id, title, app_created)
                VALUES (?, ?, ?)
                ON CONFLICT(google_album_id) DO UPDATE SET
                    title=excluded.title,
                    app_created=excluded.app_created
                """,
                (album.google_album_id, album.title, int(album.app_created)),
            )
            conn.commit()


_store = PhotoStore()


def get_photo_store() -> PhotoStore:
    """Singleton accessor for the photo store."""
    return _store
