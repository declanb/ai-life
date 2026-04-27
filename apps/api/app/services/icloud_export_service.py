"""Wraps osxphotos export to pull photos from the Mac's Photos.app library.

This service runs `osxphotos export` with flags that preserve Live Photos,
EXIF, and edited versions. It does NOT use --download-missing because we assume
the user has "Download Originals to this Mac" enabled in Photos preferences.

See osxphotos docs: https://github.com/RhetTbull/osxphotos
Flags reference: https://rhettbull.github.io/osxphotos/cli.html#osxphotos-export
"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.schemas.photo import ExportRun, Photo, PhotoState


class ICloudExportService:
    """Wraps osxphotos to export photos from iCloud Photos (synced to Mac).
    
    The canonical architecture is:
      iPhone → iCloud Photos (immutable source of truth)
             → Mac Photos.app (synced)
             → osxphotos export (this service)
             → apps/api (FastAPI in this repo)
             → Google Photos Library API (mirror, no deletes)
    """
    
    def __init__(self, export_dir: Path = Path.home() / ".ai-life-photo-exports"):
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def run_incremental_export(self, since: Optional[datetime] = None) -> ExportRun:
        """Run osxphotos export, optionally filtering to photos added since a date.
        
        osxphotos flags used:
          --export-live: export both image + video components of Live Photos
          --exiftool: preserve EXIF metadata using exiftool
          --skip-original-if-edited: export edited version instead of original (default: export both)
                                     NOT USED — we want both to preserve fidelity
          --download-missing: tell Photos to download from iCloud if not local
                              NOT USED — assume user has "Download Originals" enabled
          --update: only export new/changed photos since last run
        
        TODO: Once we have a working end-to-end dry-run, determine the exact
        flags needed. Current stub returns empty results.
        """
        run_id = str(uuid4())
        started_at = datetime.now()
        
        # TODO: Implement actual osxphotos export via subprocess
        # Example command (not executed yet):
        # cmd = [
        #     "osxphotos", "export",
        #     str(self.export_dir),
        #     "--export-live",
        #     "--exiftool",
        #     "--update",  # incremental
        # ]
        # if since:
        #     cmd.extend(["--added-after", since.isoformat()])
        #
        # result = subprocess.run(cmd, capture_output=True, text=True)
        # ... parse output, discover exported files, return ExportRun
        
        return ExportRun(
            run_id=run_id,
            started_at=started_at,
            finished_at=datetime.now(),
            exit_status=0,  # stub: success
            exported_count=0,  # stub: no photos
        )
    
    def list_exported(self, run_id: str) -> list[Photo]:
        """List photos exported during a specific run.
        
        In a real implementation, this would:
        1. Read the osxphotos export database (.osxphotos_export.db)
        2. Or parse the export directory structure
        3. Return Photo objects with DISCOVERED state
        
        For now, returns empty list (stub).
        """
        # TODO: Implement photo discovery from export output
        return []
