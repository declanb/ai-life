"""Base class for listing sources (Daft, MyHome, agent sites, fixtures)."""
from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.property_finder import Listing, RentalSpec


class SourceStatus:
    """Reportable status of a source after a fetch attempt."""
    def __init__(self, name: str, ok: bool, count: int, note: str = ""):
        self.name = name
        self.ok = ok
        self.count = count
        self.note = note

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "count": self.count, "note": self.note}


class ListingSource(ABC):
    """Abstract source. Each implementation knows how to fetch listings for a spec."""

    name: str = "base"

    @abstractmethod
    def fetch(self, spec: RentalSpec) -> tuple[list[Listing], SourceStatus]:
        """Return (listings, status). Must never raise — return empty + ok=False instead."""
        ...
