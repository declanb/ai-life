"""Trips router — manual entry + approve/reject/revert.

Capture-method-agnostic: the /trips POST endpoint accepts a canonical Trip
payload. The future Concur/TripIt parsers will internally call the same
TripStore.upsert_pending, so this API is the single write gateway.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.trip import ApprovalStatus, Trip, TripApproval
from app.services.trip_approval_service import TripApprovalService
from app.services.trip_store import TripStore, get_trip_store


router = APIRouter(prefix="/trips", tags=["trips"])


def get_approval_service() -> TripApprovalService:
    return TripApprovalService()


@router.get("", response_model=list[TripApproval])
def list_trips(store: TripStore = Depends(get_trip_store)) -> list[TripApproval]:
    return list(store.list())


@router.post("", response_model=TripApproval, status_code=201)
def create_trip(trip: Trip, store: TripStore = Depends(get_trip_store)) -> TripApproval:
    """Register a new trip as a pending approval card.

    No calendar writes happen here — approval is still required.
    """
    return store.upsert_pending(trip)


@router.get("/{trip_id}", response_model=TripApproval)
def get_trip(trip_id: str, store: TripStore = Depends(get_trip_store)) -> TripApproval:
    approval = store.get(trip_id)
    if not approval:
        raise HTTPException(404, "trip not found")
    return approval


@router.post("/{trip_id}/approve", response_model=TripApproval)
def approve_trip(
    trip_id: str,
    store: TripStore = Depends(get_trip_store),
    service: TripApprovalService = Depends(get_approval_service),
) -> TripApproval:
    approval = store.get(trip_id)
    if not approval:
        raise HTTPException(404, "trip not found")
    if approval.status == ApprovalStatus.APPLIED:
        return approval
    approval.status = ApprovalStatus.APPROVED
    try:
        approval = service.apply(approval)
    except Exception as e:
        approval.status = ApprovalStatus.PENDING
        store.set(approval)
        raise HTTPException(500, f"calendar sync failed: {e}") from e
    store.set(approval)
    return approval


@router.post("/{trip_id}/reject", response_model=TripApproval)
def reject_trip(trip_id: str, store: TripStore = Depends(get_trip_store)) -> TripApproval:
    approval = store.get(trip_id)
    if not approval:
        raise HTTPException(404, "trip not found")
    approval.status = ApprovalStatus.REJECTED
    store.set(approval)
    return approval


@router.delete("/{trip_id}", response_model=dict)
def revert_trip(
    trip_id: str,
    store: TripStore = Depends(get_trip_store),
    service: TripApprovalService = Depends(get_approval_service),
) -> dict:
    approval = store.get(trip_id)
    if not approval:
        raise HTTPException(404, "trip not found")
    removed = service.revert(approval) if approval.status == ApprovalStatus.APPLIED else 0
    approval.status = ApprovalStatus.REJECTED
    approval.event_ids = []
    store.set(approval)
    return {"removed_events": removed}
