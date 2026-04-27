"""Property Finder router: shortlist + URL-paste management + cron refresh."""
import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.schemas.property_finder import PropertyFinderResponse
from app.services.property_finder_service import (
    add_urls,
    list_urls,
    property_finder_service,
    remove_url,
)
from app.data.property_finder_discoveries import (
    get_recent_new_ids,
    get_state as get_discoveries_state,
    record_run,
)


router = APIRouter(prefix="/property-finder", tags=["property-finder"])


class AddUrlsRequest(BaseModel):
    urls: list[str]


class RemoveUrlRequest(BaseModel):
    url: str


@router.get("/shortlist", response_model=PropertyFinderResponse)
async def get_shortlist():
    """Default shortlist: IFSC, €2.5k, furnished, June 1st 2026 move-in."""
    try:
        return property_finder_service.get_shortlist()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Shortlist failed: {type(e).__name__}: {e}")


@router.get("/urls")
async def get_urls():
    return {"urls": list_urls()}


@router.post("/urls")
async def post_urls(req: AddUrlsRequest):
    count = add_urls(req.urls)
    return {"total_urls": count, "added": len(req.urls)}


@router.delete("/urls")
async def delete_url(req: RemoveUrlRequest):
    removed = remove_url(req.url)
    return {"removed": removed, "total_urls": len(list_urls())}


# ---------- Cron refresh (Vercel scheduled job) ----------

def _check_cron_auth(authorization: str | None) -> None:
    """
    Validate Vercel cron auth.

    Vercel sends `Authorization: Bearer $CRON_SECRET` to scheduled paths.
    In local dev (no CRON_SECRET set), allow unauthenticated calls so the
    refresh button on the dashboard works.
    """
    secret = os.getenv("CRON_SECRET")
    if not secret:
        return  # local dev: open
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/cron/refresh")
async def cron_refresh(authorization: str | None = Header(default=None)):
    """
    Periodic refresh: re-fetch all sources, log discoveries, return diff.

    Wired to Vercel cron at /api/v1/property-finder/cron/refresh — see vercel.json.
    """
    _check_cron_auth(authorization)
    resp = property_finder_service.get_shortlist()
    canonical_ids = [r.listing.canonical_id for r in resp.ranked_listings]
    source_summary = {s.name: {"ok": s.ok, "count": s.count} for s in resp.sources}
    diff = record_run(canonical_ids, source_summary)
    return {
        "ok": True,
        "diff": diff,
        "total_listings": len(resp.ranked_listings),
        "sources": source_summary,
    }


@router.get("/discoveries")
async def discoveries():
    """Recent 'new since last check' canonical_ids + last run timestamp."""
    state = get_discoveries_state()
    return {
        "last_run_at": state.get("last_run_at"),
        "recent_new_ids": get_recent_new_ids(limit=20),
        "events": state.get("events", [])[-10:],  # last 10 runs
    }
