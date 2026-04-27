"""Mixed fixture listings — apartments + houses across IFSC, Killester, etc."""
from datetime import date, datetime
from app.schemas.property_finder import Listing, RentalSpec
from app.services.property_finder_sources.base import ListingSource, SourceStatus


class FixturesSource(ListingSource):
    """Realistic April 2026 fixtures spanning apartments + houses. Safety net."""

    name = "fixtures"

    def fetch(self, spec: RentalSpec) -> tuple[list[Listing], SourceStatus]:
        listings = self._mixed_fixtures()
        # Filter to areas in spec (so changing area_routing_keys flips the basket)
        if spec.area_routing_keys:
            listings = [l for l in listings if l.area_routing_key in spec.area_routing_keys]
        return listings, SourceStatus(
            self.name, ok=True, count=len(listings),
            note="fixture data — paste real URLs to replace",
        )

    @staticmethod
    def _mixed_fixtures() -> list[Listing]:
        base = datetime(2026, 4, 26)
        return [
            # IFSC / Docklands apartments
            Listing(
                canonical_id="dng-custom-house-sq-studio-1950",
                source="dng",
                source_url="https://www.dng.ie/lettings/custom-house-square/FIXTURE",
                area_routing_key="D01", address_rough="Custom House Square, IFSC",
                beds=0, baths=1, rent_eur=1950, bills_included=True,
                estimated_bills_eur=0, parking_available=False, furnished=True,
                ber_rating="B1", floor_area_sqm=38, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="DNG", agent_psra="002345",
                photos_count=8, has_floor_plan=False, days_on_market=12, image_url="https://picsum.photos/seed/dng-custom-house-sq-studio-1950/640/360",
                fetched_at=base,
            ),
            Listing(
                canonical_id="myhome-mayor-square-1bed-2300",
                source="myhome",
                source_url="https://www.myhome.ie/residential/brochure/apartment-mayor-square-ifsc-dublin-1/FIXTURE",
                area_routing_key="D01", address_rough="Mayor Square, IFSC",
                beds=1, baths=1, rent_eur=2300, bills_included=False,
                estimated_bills_eur=150, parking_available=False, furnished=True,
                ber_rating="A3", floor_area_sqm=52, lease_length_months=6,
                available_from=date(2026, 5, 28),
                agent_name="DNG", agent_psra="002345",
                photos_count=15, has_floor_plan=True, days_on_market=3, image_url="https://picsum.photos/seed/myhome-mayor-square-1bed-2300/640/360",
                fetched_at=base,
            ),
            Listing(
                canonical_id="sherryfitz-castleforbes-2bed-2500",
                source="sherryfitz",
                source_url="https://www.sherryfitz.ie/lettings/dublin-1/FIXTURE",
                area_routing_key="D01", address_rough="Castleforbes Square, IFSC",
                beds=2, baths=2, rent_eur=2500, bills_included=False,
                estimated_bills_eur=180, parking_available=True, furnished=True,
                ber_rating="A2", floor_area_sqm=72, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="Sherry FitzGerald", agent_psra="001234",
                photos_count=18, has_floor_plan=True, days_on_market=5, image_url="https://picsum.photos/seed/sherryfitz-castleforbes-2bed-2500/640/360",
                fetched_at=base,
            ),
            Listing(
                canonical_id="hookemacdonald-spencer-dock-2bed-2700",
                source="hooke_macdonald",
                source_url="https://www.hookemacdonald.ie/lettings/spencer-dock-2bed/FIXTURE",
                area_routing_key="D01", address_rough="Spencer Dock, IFSC (2-bed apt)",
                beds=2, baths=2, rent_eur=2700, bills_included=False,
                estimated_bills_eur=180, parking_available=True, furnished=True,
                ber_rating="A2", floor_area_sqm=78, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="Hooke & MacDonald", agent_psra="005678",
                photos_count=20, has_floor_plan=True, days_on_market=4, image_url="https://picsum.photos/seed/hookemacdonald-spencer-dock-2bed-2700/640/360",
                fetched_at=base,
            ),

            # Killester / Brookwood houses + apartments (D05)
            Listing(
                canonical_id="daft-brookwood-meadow-3bed-house-2400",
                source="daft",
                source_url="https://www.daft.ie/for-rent/house-brookwood-meadow-killester-dublin-5/FIXTURE",
                area_routing_key="D05", address_rough="Brookwood Meadow, Killester (3-bed semi)",
                beds=3, baths=2, rent_eur=2400, bills_included=False,
                estimated_bills_eur=200, parking_available=True, furnished=True,
                ber_rating="B3", floor_area_sqm=110, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="Sherry FitzGerald", agent_psra="001234",
                photos_count=22, has_floor_plan=True, days_on_market=7, image_url="https://picsum.photos/seed/daft-brookwood-meadow-3bed-house-2400/640/360",
                fetched_at=base,
            ),
            Listing(
                canonical_id="myhome-killester-modern-house-2650",
                source="myhome",
                source_url="https://www.myhome.ie/rentals/brochure/modern-house-killester-dublin-5/FIXTURE",
                area_routing_key="D05", address_rough="Brookwood Avenue, Killester (modern 3-bed townhouse)",
                beds=3, baths=2, rent_eur=2650, bills_included=False,
                estimated_bills_eur=200, parking_available=True, furnished=True,
                ber_rating="A3", floor_area_sqm=125, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="DNG", agent_psra="002345",
                photos_count=24, has_floor_plan=True, days_on_market=2, image_url="https://picsum.photos/seed/myhome-killester-modern-house-2650/640/360",
                fetched_at=base,
            ),
            Listing(
                canonical_id="daft-killester-2bed-apt-1850",
                source="daft",
                source_url="https://www.daft.ie/for-rent/apartment-killester-dublin-5/FIXTURE",
                area_routing_key="D05", address_rough="Demesne, Killester (2-bed apartment)",
                beds=2, baths=1, rent_eur=1850, bills_included=False,
                estimated_bills_eur=140, parking_available=True, furnished=True,
                ber_rating="C1", floor_area_sqm=68, lease_length_months=12,
                available_from=date(2026, 6, 1),
                agent_name="Lisney", agent_psra="003890",
                photos_count=12, has_floor_plan=True, days_on_market=8, image_url="https://picsum.photos/seed/daft-killester-2bed-apt-1850/640/360",
                fetched_at=base,
            ),

            # East Wall / North Strand (D03) — bridge between IFSC and Killester
            Listing(
                canonical_id="myhome-east-wall-2bed-house-2200",
                source="myhome",
                source_url="https://www.myhome.ie/rentals/brochure/east-wall-house-dublin-3/FIXTURE",
                area_routing_key="D03", address_rough="East Wall, Dublin 3 (2-bed redbrick)",
                beds=2, baths=1, rent_eur=2200, bills_included=False,
                estimated_bills_eur=170, parking_available=False, furnished=True,
                ber_rating="C2", floor_area_sqm=85, lease_length_months=12,
                available_from=date(2026, 6, 5),
                agent_name="DNG", agent_psra="002345",
                photos_count=14, has_floor_plan=True, days_on_market=4, image_url="https://picsum.photos/seed/myhome-east-wall-2bed-house-2200/640/360",
                fetched_at=base,
            ),

            # Stoneybatter (D07) — modern house option north-west
            Listing(
                canonical_id="sherryfitz-stoneybatter-modern-2350",
                source="sherryfitz",
                source_url="https://www.sherryfitz.ie/lettings/stoneybatter-modern/FIXTURE",
                area_routing_key="D07", address_rough="Manor Street, Stoneybatter (modern 2-bed mews)",
                beds=2, baths=2, rent_eur=2350, bills_included=False,
                estimated_bills_eur=160, parking_available=False, furnished=True,
                ber_rating="A3", floor_area_sqm=82, lease_length_months=12,
                available_from=date(2026, 5, 30),
                agent_name="Sherry FitzGerald", agent_psra="001234",
                photos_count=18, has_floor_plan=True, days_on_market=3, image_url="https://picsum.photos/seed/sherryfitz-stoneybatter-modern-2350/640/360",
                fetched_at=base,
            ),
        ]

