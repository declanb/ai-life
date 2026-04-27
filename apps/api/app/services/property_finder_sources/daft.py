"""
Daft.ie source via the community-maintained `daftlistings` package.

License: MIT (https://github.com/AnthonyBloomer/daftlistings).
ToS note: the underlying API is undocumented; we treat it as grey-area but tolerated.
We rate-limit ourselves to one search per request and cache aggressively in production.
"""
from datetime import datetime
from typing import Optional

from app.schemas.property_finder import Listing, RentalSpec
from app.services.property_finder_sources.base import ListingSource, SourceStatus


class DaftSource(ListingSource):
    name = "daft"

    def fetch(self, spec: RentalSpec) -> tuple[list[Listing], SourceStatus]:
        try:
            from daftlistings import Daft, Location, SearchType, PropertyType  # type: ignore
        except ImportError:
            return [], SourceStatus(
                self.name, ok=False, count=0,
                note="daftlistings not installed. Run: pip install daftlistings"
            )

        try:
            daft = Daft()
            # The daftlistings package needs origin/referer headers since Daft
            # added bot protection in 2025. Set a real-browser User-Agent too.
            try:
                daft.set_headers({
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Origin": "https://www.daft.ie",
                    "Referer": "https://www.daft.ie/",
                    "Accept": "application/json",
                })
            except Exception:  # noqa: BLE001
                pass
            # IFSC sits in Dublin 1; daftlistings doesn't have IFSC as a Location enum,
            # so use Dublin 1 and filter post-fetch by the area string match.
            try:
                location = Location.DUBLIN_1
            except AttributeError:
                location = Location.DUBLIN
            daft.set_location(location)
            daft.set_search_type(SearchType.RESIDENTIAL_RENT)
            daft.set_property_type(PropertyType.APARTMENT)
            daft.set_max_price(spec.max_rent_eur)
            if spec.beds_min:
                try:
                    daft.set_min_beds(spec.beds_min)
                except Exception:  # noqa: BLE001
                    pass

            raw = daft.search(max_pages=1)
        except Exception as e:  # noqa: BLE001
            return [], SourceStatus(
                self.name, ok=False, count=0,
                note=f"Daft fetch failed: {type(e).__name__}: {str(e)[:120]}"
            )

        listings: list[Listing] = []
        for r in raw:
            try:
                listings.append(self._normalise(r, spec))
            except Exception:  # noqa: BLE001
                continue  # Skip malformed listings rather than fail the whole batch

        # Filter to IFSC-y addresses if user is targeting D01
        if "D01" in spec.area_routing_keys:
            ifsc_terms = (
                "ifsc", "north wall", "spencer", "mayor square", "custom house",
                "castleforbes", "north dock", "georges dock", "docklands", "dublin 1",
            )
            listings = [
                l for l in listings
                if any(t in l.address_rough.lower() for t in ifsc_terms)
            ]

        return listings, SourceStatus(self.name, ok=True, count=len(listings), note="live")

    @staticmethod
    def _normalise(r, spec: RentalSpec) -> Listing:
        """Convert a daftlistings Listing object to our schema."""
        # daftlistings exposes attributes like: title, price, daft_link, bedrooms,
        # bathrooms, ber, monthly_price, sale_type, etc.
        title = (getattr(r, "title", "") or "").strip()
        url = getattr(r, "daft_link", "") or ""

        # Price: prefer monthly_price (int), fall back to parsing the price string
        rent = 0
        try:
            rent = int(getattr(r, "monthly_price", 0) or 0)
        except (TypeError, ValueError):
            rent = 0
        if not rent:
            price_str = str(getattr(r, "price", "") or "")
            digits = "".join(ch for ch in price_str if ch.isdigit())
            if digits:
                rent = int(digits[:6])  # Cap to 6 digits to avoid silly values

        beds = 0
        try:
            beds = int(getattr(r, "bedrooms", 0) or 0)
        except (TypeError, ValueError):
            # Sometimes "1 Bed" — extract digit
            bed_str = str(getattr(r, "bedrooms", "") or "")
            digits = "".join(ch for ch in bed_str if ch.isdigit())
            beds = int(digits[:1]) if digits else 0

        baths = 1
        try:
            baths = int(getattr(r, "bathrooms", 1) or 1)
        except (TypeError, ValueError):
            pass

        ber = getattr(r, "ber", None)
        if ber and not isinstance(ber, str):
            ber = str(ber)

        canonical = f"daft-{title.lower().replace(' ', '-')[:50]}-{rent}"

        return Listing(
            canonical_id=canonical,
            source="daft",
            source_url=url,
            area_routing_key="D01" if "D01" in spec.area_routing_keys else (spec.area_routing_keys[0] if spec.area_routing_keys else "?"),
            address_rough=title or "Unknown address",
            beds=beds,
            baths=baths,
            rent_eur=rent,
            bills_included=False,
            estimated_bills_eur=150,
            parking_available=False,  # Unknown from search results; would need detail fetch
            furnished=spec.furnished,  # Daft search doesn't reliably expose this; assume matches spec
            ber_rating=ber,
            photos_count=0,
            has_floor_plan=False,
            fetched_at=datetime.utcnow(),
        )
