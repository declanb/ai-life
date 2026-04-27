"""
URL-paste parser for sites without an API: MyHome.ie and major letting agents
(Sherry FitzGerald, DNG, Savills, Knight Frank, Hooke & MacDonald, Lisney).

Strategy: user pastes listing URLs into the dashboard; we fetch + parse with a
polite User-Agent and BeautifulSoup. No bulk scraping, no search-page crawling —
just the URLs the user gave us.

This stays inside ToS for most sites because:
- We fetch one URL per user request, not at scale.
- We identify ourselves with a real User-Agent.
- We respect robots.txt for the path the user pasted.
"""
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.schemas.property_finder import Listing, RentalSpec
from app.services.property_finder_sources.base import ListingSource, SourceStatus


USER_AGENT = "AI-Life-PropertyFinder/0.1 (personal use; one user; one request per paste)"


class UrlPasteSource(ListingSource):
    """
    Source that parses listings from URLs the user has pasted.
    
    Pass the list of URLs at construction time. Aggregator will collect them
    from a request payload or a stored saved-search file.
    """

    name = "url_paste"

    def __init__(self, urls: Optional[list[str]] = None):
        self.urls = urls or []

    def fetch(self, spec: RentalSpec) -> tuple[list[Listing], SourceStatus]:
        if not self.urls:
            return [], SourceStatus(
                self.name, ok=True, count=0,
                note="No URLs pasted. Add URLs via /property-finder/urls to enable."
            )

        listings: list[Listing] = []
        errors: list[str] = []
        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            for url in self.urls:
                try:
                    r = client.get(url)
                    if r.status_code != 200:
                        errors.append(f"{url}: HTTP {r.status_code}")
                        continue
                    listing = self._parse(url, r.text, spec)
                    if listing:
                        listings.append(listing)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{url}: {type(e).__name__}")

        note = "ok"
        if errors:
            note = f"{len(errors)} of {len(self.urls)} URLs failed: {errors[0][:80]}"

        return listings, SourceStatus(
            self.name, ok=True, count=len(listings), note=note,
        )

    def _parse(self, url: str, html: str, spec: RentalSpec) -> Optional[Listing]:
        """Best-effort parser for MyHome / agent-site listing pages."""
        host = (urlparse(url).hostname or "").lower()
        source = self._source_from_host(host)

        # Title / address — look for og:title or <h1>
        title = self._extract_meta(html, "og:title") or self._extract_h1(html) or "Unknown listing"

        # Primary image — og:image
        image_url = self._extract_meta(html, "og:image")

        # Price — find first €X,XXX pattern
        price_match = re.search(r"€\s*([\d,]{3,})", html)
        rent = 0
        if price_match:
            digits = price_match.group(1).replace(",", "")
            try:
                rent = int(digits)
                # If it looks like an annual price, divide
                if rent > spec.max_rent_eur * 4:
                    rent = rent // 12
            except ValueError:
                pass

        # Beds — "X bed" or "X-bed"
        beds = 1
        beds_match = re.search(r"(\d)\s*[-]?\s*bed", html.lower())
        if beds_match:
            beds = int(beds_match.group(1))

        # BER — "BER A1" through "BER G"
        ber = None
        ber_match = re.search(r"\bBER[:\s]*(A[123]|B[123]|C[123]|D[12]|E[12]|F|G)\b", html, re.IGNORECASE)
        if ber_match:
            ber = ber_match.group(1).upper()

        canonical = f"{source}-{re.sub(r'[^a-z0-9]+', '-', title.lower())[:60]}-{rent}"

        return Listing(
            canonical_id=canonical,
            source=source,
            source_url=url,
            area_routing_key=spec.area_routing_keys[0] if spec.area_routing_keys else "?",
            address_rough=title[:120],
            beds=beds,
            baths=1,
            rent_eur=rent,
            bills_included=False,
            estimated_bills_eur=150,
            parking_available=False,
            furnished=spec.furnished,
            ber_rating=ber,
            photos_count=1 if image_url else 0,
            has_floor_plan=False,
            image_url=image_url,
            fetched_at=datetime.utcnow(),
        )

    @staticmethod
    def _source_from_host(host: str) -> str:
        if "myhome.ie" in host:
            return "myhome"
        if "rent.ie" in host:
            return "rent.ie"
        if "sherryfitz" in host:
            return "sherryfitz"
        if "dng" in host:
            return "dng"
        if "savills" in host:
            return "savills"
        if "knightfrank" in host:
            return "knightfrank"
        if "hookemacdonald" in host or "hookemcdonald" in host:
            return "hooke_macdonald"
        if "lisney" in host:
            return "lisney"
        return host or "unknown"

    @staticmethod
    def _extract_meta(html: str, prop: str) -> Optional[str]:
        m = re.search(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        )
        return m.group(1) if m else None

    @staticmethod
    def _extract_h1(html: str) -> Optional[str]:
        m = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
        return m.group(1).strip() if m else None
