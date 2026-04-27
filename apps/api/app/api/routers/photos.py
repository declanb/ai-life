"""FastAPI router for the iCloud → Google Photos mirror feature.

Endpoints:
  GET  /photos/sync/status  — last sync status + counts
  POST /photos/sync/run     — trigger a sync (dry-run by default)
  GET  /photos/exports      — list export runs
  GET  /photos/uploads      — list upload records

No delete endpoints (Google Photos API does not support deletion).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.photo_sync_service import PhotoSyncService
from app.schemas.photo import SyncStatus


router = APIRouter(prefix="/photos", tags=["photos"])


def get_sync_service():
    return PhotoSyncService()


class RunSyncRequest(BaseModel):
    """Request body for POST /photos/sync/run."""
    dry_run: bool = True


@router.get("/sync/status")
async def get_sync_status(service: PhotoSyncService = Depends(get_sync_service)) -> SyncStatus:
    """Get the current sync status (counts, last run, etc.)."""
    try:
        # TODO: Fetch actual status from photo_store
        # For now, returns stub data matching the service stub
        return service.run_sync(dry_run=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/run")
async def run_sync(
    request: RunSyncRequest,
    service: PhotoSyncService = Depends(get_sync_service)
) -> dict:
    """Trigger a sync run.
    
    By default, dry_run=True. Set dry_run=false to actually upload to Google Photos.
    """
    try:
        status = service.run_sync(dry_run=request.dry_run)
        return {
            "message": f"Sync completed ({'dry-run' if request.dry_run else 'live'})",
            "status": status.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exports")
async def list_exports() -> dict:
    """List all osxphotos export runs.
    
    TODO: Query photo_store for export_run records.
    """
    return {"exports": []}


@router.get("/uploads")
async def list_uploads() -> dict:
    """List all upload records.
    
    TODO: Query photo_store for upload records.
    """
    return {"uploads": []}
