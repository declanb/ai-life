"""In-memory Trip Approval store.

Placeholder for a proper DB. Good enough for the first vertical slice; swap for
SQLite/Postgres once schema stabilises.
"""
from __future__ import annotations

from threading import Lock
from typing import Iterable

from app.schemas.trip import ApprovalStatus, Trip, TripApproval


class TripStore:
    def __init__(self) -> None:
        self._items: dict[str, TripApproval] = {}
        self._lock = Lock()

    def upsert_pending(self, trip: Trip) -> TripApproval:
        with self._lock:
            existing = self._items.get(trip.id)
            if existing and existing.status in (ApprovalStatus.APPLIED, ApprovalStatus.APPROVED):
                # don't silently overwrite an approved trip
                return existing
            approval = TripApproval(trip=trip, status=ApprovalStatus.PENDING)
            self._items[trip.id] = approval
            return approval

    def get(self, trip_id: str) -> TripApproval | None:
        return self._items.get(trip_id)

    def set(self, approval: TripApproval) -> None:
        with self._lock:
            self._items[approval.trip.id] = approval

    def list(self) -> Iterable[TripApproval]:
        return list(self._items.values())


_store = TripStore()


def get_trip_store() -> TripStore:
    return _store
