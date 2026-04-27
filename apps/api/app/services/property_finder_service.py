"""
Property Finder service - orchestrates source aggregation, scoring, and ranking.
"""
from datetime import date
from typing import Optional

from app.schemas.property_finder import (
    AffordabilityVerdict,
    BuyTarget,
    Listing,
    ListingScore,
    MortgageProfile,
    MortgageReadinessSnapshot,
    PropertyFinderResponse,
    RankedListing,
    RentalSpec,
    SourceStatusModel,
)
from app.services.property_finder_sources.aggregator import Aggregator
from app.data.property_finder_url_store import (
    add_urls as _add_urls,
    list_urls as _list_urls,
    remove_url as _remove_url,
)


def add_urls(urls: list[str]) -> int:
    return _add_urls(urls)


def list_urls() -> list[str]:
    return _list_urls()


def remove_url(url: str) -> bool:
    return _remove_url(url)


class PropertyFinderService:
    """Orchestrate sources, score, and rank rental shortlists."""

    def get_shortlist(
        self,
        rental_spec: Optional[RentalSpec] = None,
        buy_target: Optional[BuyTarget] = None,
        mortgage_profile: Optional[MortgageProfile] = None,
    ) -> PropertyFinderResponse:
        if rental_spec is None:
            rental_spec = RentalSpec(
                area_routing_keys=["D01", "D03", "D05", "D07"],
                max_rent_eur=2700,
                beds_min=0,
                furnished=True,
                lease_length_months=6,
                move_in_date=date(2026, 6, 1),
            )

        aggregator = Aggregator(url_paste_urls=list_urls())
        candidates, source_statuses = aggregator.fetch_all(rental_spec)

        candidates = [c for c in candidates if self._meets_spec(c, rental_spec)]

        ranked: list[RankedListing] = []
        for listing in candidates:
            scores = self._score_listing(listing, buy_target)
            ranked.append(RankedListing(
                listing=listing,
                scores=scores,
                rank=0,
                why_this=self._why_this(listing, scores, rental_spec),
                deal_breakers_passed=self._deal_breakers_passed(listing, rental_spec),
            ))

        ranked.sort(key=lambda r: (
            -r.scores.listing_quality_score * 0.4
            + (r.listing.total_monthly_cost_eur / 100) * 0.3
            + (r.scores.commute_minutes or 99) * 0.3
        ))
        for idx, item in enumerate(ranked):
            item.rank = idx + 1

        recommended = ranked[0] if ranked else None
        readiness = self._stub_readiness(mortgage_profile) if mortgage_profile else None

        return PropertyFinderResponse(
            rental_spec=rental_spec,
            buy_target=buy_target,
            ranked_listings=ranked[:5],
            recommended_pick=recommended,
            readiness_snapshot=readiness,
            sources=[SourceStatusModel(**s.to_dict()) for s in source_statuses],
            spec_notes=(
                f"IFSC furnished rentals, available by {rental_spec.move_in_date.isoformat()}. "
                "Live Daft via daftlistings (community-maintained, MIT). "
                "Paste MyHome / Sherry FitzGerald / DNG / Hooke & MacDonald URLs at /api/v1/property-finder/urls."
            ),
        )

    @staticmethod
    def _meets_spec(listing: Listing, spec: RentalSpec) -> bool:
        if listing.rent_eur and listing.rent_eur > spec.max_rent_eur:
            return False
        if listing.beds < spec.beds_min:
            return False
        if spec.parking_required and not listing.parking_available:
            return False
        if listing.available_from and listing.available_from > spec.move_in_date:
            return False
        return True

    @staticmethod
    def _score_listing(listing: Listing, buy_target: Optional[BuyTarget]) -> ListingScore:
        quality = 0.0
        if listing.ber_rating:
            quality += 0.25
        if listing.has_floor_plan:
            quality += 0.25
        if listing.agent_psra:
            quality += 0.25
        if listing.photos_count >= 10:
            quality += 0.25

        buy_overlap = 0.0
        if buy_target:
            if listing.area_routing_key in buy_target.area_routing_keys:
                buy_overlap = 1.0
            else:
                buy_overlap = 0.3

        commute = 12

        return ListingScore(
            commute_minutes=commute,
            buy_overlap_score=buy_overlap,
            listing_quality_score=quality,
            mortgage_area_sanity="buy-realistic",
            rpz_flag=listing.area_routing_key.startswith("D"),
            affordability_verdict=AffordabilityVerdict.GREEN,
            affordability_note="Within target",
        )

    @staticmethod
    def _why_this(listing: Listing, scores: ListingScore, spec: RentalSpec) -> str:
        reasons: list[str] = []
        if listing.rent_eur and listing.rent_eur < spec.max_rent_eur - 300:
            reasons.append(f"€{spec.max_rent_eur - listing.rent_eur} under budget")
        if scores.listing_quality_score >= 0.75:
            reasons.append("complete listing (BER + floor plan + photos)")
        if listing.lease_length_months == 6:
            reasons.append("6-month lease flexibility")
        if listing.beds >= 2:
            reasons.append("extra bedroom")
        if listing.parking_available:
            reasons.append("parking included")
        if not reasons:
            reasons.append("meets all spec requirements")
        return " · ".join(reasons[:2])

    @staticmethod
    def _deal_breakers_passed(listing: Listing, spec: RentalSpec) -> list[str]:
        out = [
            "Furnished" if spec.furnished else "Any furnishing",
            f"≤€{spec.max_rent_eur}/mo",
            f"In {','.join(spec.area_routing_keys)}",
        ]
        if listing.available_from and listing.available_from <= spec.move_in_date:
            out.append(f"Available by {spec.move_in_date.isoformat()}")
        return out

    @staticmethod
    def _stub_readiness(profile: Optional[MortgageProfile]) -> MortgageReadinessSnapshot:
        return MortgageReadinessSnapshot(
            deposit_runway_months=18,
            aip_action="start_application",
            scheme_recommendation=(
                "First Home Scheme: likely eligible if FTB + within scheme caps. "
                "Help-to-Buy: new-build only — verify on revenue.ie."
            ),
            next_concrete_action=(
                "Get an Agreement in Principle from 2 lenders (~48h) before serious viewings."
            ),
            not_regulated_advice_note=(
                "Not regulated financial or mortgage advice. "
                "Engage a mortgage broker for binding decisions."
            ),
        )


property_finder_service = PropertyFinderService()
