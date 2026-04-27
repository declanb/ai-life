"""Free day planner schemas.

Surfaces shopping opportunities and local activities when the user
has free time during a work trip.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    SHOPPING = "shopping"
    ACTIVITY = "activity"
    DINING = "dining"


class ShoppingCategory(str, Enum):
    TRAVEL_ESSENTIALS = "travel_essentials"  # forgot toothbrush, need adaptor
    LOCAL_SPECIALTY = "local_specialty"      # Munich outdoor gear, traditional items
    GIFTS = "gifts"                          # souvenirs, items to bring back
    REPLACEMENT = "replacement"              # something broke, need replacement
    WARDROBE = "wardrobe"                    # clothes, shoes
    ELECTRONICS = "electronics"              # gadgets, cables, chargers


class ActivityCategory(str, Enum):
    SIGHTSEEING = "sightseeing"              # museums, landmarks
    OUTDOOR = "outdoor"                       # parks, hiking, biking
    CULTURE = "culture"                       # galleries, theatre, music
    FOOD = "food"                            # restaurants, food markets
    SHOPPING_DISTRICT = "shopping_district"   # retail areas to browse
    DAY_TRIP = "day_trip"                    # nearby towns, attractions


class PriceLevel(str, Enum):
    BUDGET = "budget"        # €/£/$
    MODERATE = "moderate"    # €€/££/$$
    PREMIUM = "premium"      # €€€/£££/$$$


class ShoppingRecommendation(BaseModel):
    title: str = Field(..., description="Item or store name")
    category: ShoppingCategory
    description: str = Field(..., description="Why you need this / what makes it good value")
    price_estimate: Optional[str] = None  # "€25-35", "from £50"
    price_level: PriceLevel = PriceLevel.MODERATE
    location: str = Field(..., description="Store name or shopping district")
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    distance_from_hotel: Optional[str] = None  # "5 min walk", "15 min by U-Bahn"
    url: Optional[str] = None
    confidence_score: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="How confident we are this is good value / relevant",
    )
    reasoning: str = Field(
        ..., description="Why this is recommended right now (gap in wardrobe, local price advantage, etc.)"
    )


class ActivityRecommendation(BaseModel):
    title: str = Field(..., description="Activity or venue name")
    category: ActivityCategory
    description: str = Field(..., description="What you'll experience / why it's worth it")
    price_estimate: Optional[str] = None  # "Free", "€15 entry", "€30-50/person"
    price_level: PriceLevel = PriceLevel.MODERATE
    duration: str = Field(..., description="How long it takes: '2 hours', '4-5 hours', 'full day'")
    location: str = Field(..., description="Venue or area name")
    address: Optional[str] = None
    distance_from_hotel: Optional[str] = None  # "5 min walk", "30 min by S-Bahn"
    url: Optional[str] = None
    booking_required: bool = False
    best_time: Optional[str] = None  # "Morning (less crowded)", "Evening (sunset)"
    confidence_score: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="How confident we are this suits the user",
    )
    reasoning: str = Field(
        ..., description="Why this is recommended (matches interests, unique to location, etc.)"
    )


class FreeDayContext(BaseModel):
    """Context about the user's current travel situation."""

    location: str = Field(..., description="City, Country")
    trip_id: Optional[str] = None
    trip_title: Optional[str] = None
    hotel_name: Optional[str] = None
    hotel_address: Optional[str] = None
    date: str = Field(..., description="ISO date of the free day")
    time_available: str = Field(
        ..., description="When they're free: 'All day', 'Morning', 'Afternoon 2pm onwards'"
    )
    weather: Optional[str] = None  # "Sunny, 18°C", "Rainy, 12°C"
    local_time: datetime = Field(default_factory=datetime.utcnow)


class FreeDayPlan(BaseModel):
    """Complete free day plan with context + recommendations."""

    context: FreeDayContext
    shopping_recommendations: list[ShoppingRecommendation] = Field(default_factory=list)
    activity_recommendations: list[ActivityRecommendation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
