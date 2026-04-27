"""Free day planner router.

Provides shopping and activity recommendations when the user has free time
during a work trip.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.free_day import FreeDayPlan
from app.services.free_day_planner_service import FreeDayPlannerService

router = APIRouter(prefix="/free-days", tags=["free-days"])


@router.get("/plan", response_model=FreeDayPlan)
def get_free_day_plan(
    location: str = Query(
        ...,
        description="City name (e.g., 'Munich', 'London', 'New York')",
        examples=["Munich"],
    ),
    date: Optional[str] = Query(
        None,
        description="ISO date for the free day (defaults to today)",
        examples=["2026-04-27"],
    ),
    time_available: str = Query(
        "All day",
        description="Time window available",
        examples=["All day", "Morning", "Afternoon 2pm onwards"],
    ),
) -> FreeDayPlan:
    """
    Generate a free-day plan with shopping and activity recommendations.
    
    Returns curated, high-confidence recommendations for:
    - Shopping opportunities (travel essentials, local specialties, gifts)
    - Activities (sightseeing, dining, day trips)
    
    Filtered by location and time available.
    """
    try:
        service = FreeDayPlannerService()
        plan = service.generate_plan(
            location=location,
            date=date,
            time_available=time_available,
        )
        
        if not plan.shopping_recommendations and not plan.activity_recommendations:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations available for {location} yet. "
                       "Currently supported: Munich. More cities coming soon.",
            )
        
        return plan
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-cities")
def get_supported_cities() -> dict[str, list[str]]:
    """
    List cities with curated recommendations.
    """
    service = FreeDayPlannerService()
    return {"cities": list(service.CITY_DATA.keys())}
