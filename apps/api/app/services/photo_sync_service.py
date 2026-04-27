"""Orchestrates the iCloud → Google Photos sync state machine.

State machine (per photo):
  discovered → exported → hashed → uploaded → verified
  
  Failure states:
    failed_export, failed_hash, failed_upload (each can retry)

The default mode is dry_run=True to avoid accidental uploads.
"""
from __future__ import annotations

from app.schemas.photo import SyncStatus
from app.services.icloud_export_service import ICloudExportService
from app.services.google_photos_service import GooglePhotosService
from app.services.photo_store import get_photo_store


class PhotoSyncService:
    """Orchestrates the photo sync state machine.
    
    Canonical flow:
      1. Run osxphotos export (via ICloudExportService)
      2. For each exported photo:
         a. Compute SHA-256 + perceptual hash (state: hashed)
         b. Check if already uploaded (via GooglePhotosService.list_app_created_items)
         c. If not, upload (state: uploaded)
         d. Verify upload succeeded (state: verified)
      3. Update PhotoStore with new states
      4. Return SyncStatus summary
    """
    
    def __init__(self):
        self.export_service = ICloudExportService()
        self.google_service = GooglePhotosService()
        self.store = get_photo_store()
    
    def run_sync(self, dry_run: bool = True) -> SyncStatus:
        """Run the sync pipeline.
        
        Args:
            dry_run: If True, do NOT upload anything to Google Photos.
                     Only export from iCloud and compute hashes.
        
        Returns:
            SyncStatus with counts and last run metadata.
        
        TODO: Implement actual state machine. Currently returns stub data.
        """
        # Stub implementation
        # In a real implementation:
        # 1. run_id = self.export_service.run_incremental_export()
        # 2. photos = self.export_service.list_exported(run_id)
        # 3. For each photo:
        #      - compute hashes
        #      - store.upsert_photo(photo)
        #      - if not dry_run: google_service.upload_media(photo)
        # 4. Return summary
        
        return SyncStatus(
            last_export_run_id=None,
            total_photos_discovered=0,
            total_photos_exported=0,
            total_photos_uploaded=0,
            pending_uploads=0,
            failed_photos=0,
            last_sync_at=None,
        )
