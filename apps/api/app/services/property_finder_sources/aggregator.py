"""Aggregator: run all sources, dedupe, return combined listings + per-source status."""
from typing import Optional

from app.schemas.property_finder import Listing, RentalSpec
from app.services.property_finder_sources.base import ListingSource, SourceStatus
from app.services.property_finder_sources.daft import DaftSource
from app.services.property_finder_sources.url_paste import UrlPasteSource
from app.services.property_finder_sources.fixtures import FixturesSource


class Aggregator:
    """
    Combines listings from multiple sources, dedupes by canonical key, and reports
    per-source status so the dashboard can show what worked.
    """

    def __init__(
        self,
        url_paste_urls: Optional[list[str]] = None,
        include_fixtures_fallback: bool = True,
    ):
        self.sources: list[ListingSource] = [
            DaftSource(),
            UrlPasteSource(urls=url_paste_urls or []),
        ]
        self.include_fixtures_fallback = include_fixtures_fallback

    def fetch_all(self, spec: RentalSpec) -> tuple[list[Listing], list[SourceStatus]]:
        all_listings: list[Listing] = []
        statuses: list[SourceStatus] = []

        for source in self.sources:
            listings, status = source.fetch(spec)
            statuses.append(status)
            all_listings.extend(listings)

        # Fallback to fixtures if live sources returned nothing
        if not all_listings and self.include_fixtures_fallback:
            fixture_source = FixturesSource()
            listings, status = fixture_source.fetch(spec)
            statuses.append(status)
            all_listings.extend(listings)

        # Dedupe by canonical_id
        seen: set[str] = set()
        deduped: list[Listing] = []
        for listing in all_listings:
            if listing.canonical_id in seen:
                continue
            seen.add(listing.canonical_id)
            deduped.append(listing)

        return deduped, statuses
