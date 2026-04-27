"""
Property Finder schemas for rental search and mortgage readiness.
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AffordabilityVerdict(str, Enum):
    """Affordability verdict from Personal Finances subagent."""
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class RentalSpec(BaseModel):
    """User's rental search specification."""
    area_routing_keys: list[str] = Field(description="Eircode routing keys (e.g. ['D01', 'D02'])")
    max_rent_eur: int = Field(description="Maximum monthly rent in EUR")
    beds_min: int = Field(default=1, description="Minimum bedrooms")
    furnished: bool = Field(default=True, description="Furnished required")
    lease_length_months: int = Field(default=6, description="Target lease length")
    move_in_date: date = Field(description="Required move-in date")
    parking_required: bool = Field(default=False)
    pets_allowed: bool = Field(default=False)
    ber_floor: Optional[str] = Field(default=None, description="Minimum BER rating (A1, A2, ... G)")


class Listing(BaseModel):
    """A single property listing, normalized across sources."""
    canonical_id: str = Field(description="Stable ID: source + rough address + price band")
    source: str = Field(description="daft | myhome | rent.ie | hap.ie | airbnb | spotahome")
    source_url: str
    area_routing_key: str = Field(description="Eircode routing key (e.g. D01)")
    address_rough: str = Field(description="Building + street, no full Eircode")
    beds: int
    baths: int
    rent_eur: int = Field(description="Monthly rent as listed")
    bills_included: bool = Field(default=False)
    estimated_bills_eur: int = Field(default=150, description="Estimate if not included")
    parking_available: bool
    furnished: bool
    ber_rating: Optional[str] = Field(default=None)
    floor_area_sqm: Optional[int] = Field(default=None)
    lease_length_months: Optional[int] = Field(default=None, description="Stated lease length if known")
    available_from: Optional[date] = Field(default=None)
    agent_name: Optional[str] = Field(default=None)
    agent_psra: Optional[str] = Field(default=None, description="PSRA number if Irish agent")
    photos_count: int = Field(default=0)
    has_floor_plan: bool = Field(default=False)
    days_on_market: Optional[int] = Field(default=None)
    image_url: Optional[str] = Field(default=None, description="Primary listing image (og:image or first gallery photo)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_monthly_cost_eur(self) -> int:
        """Rent + bills (estimated if not included)."""
        if self.bills_included:
            return self.rent_eur
        return self.rent_eur + self.estimated_bills_eur


class ListingScore(BaseModel):
    """Computed scores for ranking a listing."""
    commute_minutes: Optional[int] = Field(default=None, description="To target point, target mode")
    buy_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0, 
                                      description="1.0 = same area as buy target, 0.0 = different city")
    listing_quality_score: float = Field(default=0.0, ge=0.0, le=1.0,
                                          description="Has BER, floor plan, agent, photos")
    mortgage_area_sanity: str = Field(default="unknown", 
                                       description="buy-realistic | too-expensive | no-data")
    rpz_flag: bool = Field(default=False, description="Area is in Rent Pressure Zone")
    affordability_verdict: Optional[AffordabilityVerdict] = Field(default=None)
    affordability_note: Optional[str] = Field(default=None)


class RankedListing(BaseModel):
    """A listing with scores and ranking metadata."""
    listing: Listing
    scores: ListingScore
    rank: int
    why_this: str = Field(description="Human-readable reason for ranking")
    deal_breakers_passed: list[str] = Field(default_factory=list)


class BuyTarget(BaseModel):
    """User's eventual purchase target (for buy-overlap scoring)."""
    window_months: int = Field(description="Months until target purchase")
    budget_band_eur: str = Field(description="e.g. '€400k–€475k'")
    area_routing_keys: list[str] = Field(description="Target areas for purchase")
    beds_min: int = Field(default=2)
    ber_floor: Optional[str] = Field(default=None)


class MortgageProfile(BaseModel):
    """User's mortgage readiness (bands only, never raw figures)."""
    deposit_pct_of_target: str = Field(description="e.g. '8–12%'")
    lti_multiple_used: str = Field(description="e.g. '3.0–3.5x'")
    aip_days_remaining: Optional[int] = Field(default=None, description="Days until AIP expires, None if no AIP")
    monthly_savings_band: str = Field(description="e.g. '€800–€1200'")
    first_time_buyer: bool = Field(default=True)
    help_to_buy_eligible: bool = Field(default=False)
    first_home_scheme_eligible: bool = Field(default=False)
    laap_eligible: bool = Field(default=False)


class MortgageReadinessSnapshot(BaseModel):
    """Output from Personal Finances subagent."""
    deposit_runway_months: Optional[int] = Field(default=None, 
                                                   description="Months to hit target deposit at current savings rate")
    aip_action: str = Field(description="none | refresh_now | refresh_in_30d | start_application")
    scheme_recommendation: str = Field(description="HtB / FHS / LAAP applicability summary")
    next_concrete_action: str = Field(description="Single most valuable thing to do next")
    not_regulated_advice_note: str = Field(default="This analysis is not regulated financial or mortgage advice. Engage a mortgage broker for binding decisions.")


class SourceStatusModel(BaseModel):
    """Per-source fetch status for the dashboard."""
    name: str
    ok: bool
    count: int
    note: str = ""


class PropertyFinderResponse(BaseModel):
    """Complete response: shortlist + readiness snapshot."""
    rental_spec: RentalSpec
    buy_target: Optional[BuyTarget] = Field(default=None)
    ranked_listings: list[RankedListing]
    recommended_pick: Optional[RankedListing] = Field(default=None)
    readiness_snapshot: Optional[MortgageReadinessSnapshot] = Field(default=None)
    sources: list[SourceStatusModel] = Field(default_factory=list)
    spec_notes: str = Field(default="")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
