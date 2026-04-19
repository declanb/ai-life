from fastapi import APIRouter, HTTPException, Depends
from app.services.transit_service import TransitService
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/transit", tags=["transit"])

class CommuteRequest(BaseModel):
    origin_stop: str
    route: Optional[str] = None
    destination: Optional[str] = None
    walk_minutes: int = 5
    mode: str = "bus"

def get_transit_service():
    return TransitService()

@router.get("/bus/stop/{stop_id}")
async def get_bus_stop_departures(
    stop_id: str,
    service: TransitService = Depends(get_transit_service)
):
    try:
        return service.get_bus_departures(stop_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/luas/stop/{abbrev}")
async def get_luas_stop_departures(
    abbrev: str,
    service: TransitService = Depends(get_transit_service)
):
    try:
        return service.get_luas_departures(abbrev.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_stops(
    query: str,
    service: TransitService = Depends(get_transit_service)
):
    try:
        return service.search_stops(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/commute")
async def plan_commute(
    request: CommuteRequest,
    service: TransitService = Depends(get_transit_service)
):
    try:
        return service.suggest_commute(
            origin_stop=request.origin_stop,
            route=request.route,
            destination=request.destination,
            walk_minutes=request.walk_minutes,
            mode=request.mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/commute/to-work")
async def get_commute_to_work(
    service: TransitService = Depends(get_transit_service)
):
    """
    Get personalised commute options from Coolock home to Harcourt St work.
    Returns top 3 bus options (15/15A/15B) with leave-at times.
    """
    try:
        return service.get_commute_to_work()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/commute/to-home")
async def get_commute_to_home(
    service: TransitService = Depends(get_transit_service)
):
    """
    Get personalised commute options from Harcourt St work to Coolock home.
    Returns top 3 Luas options from HAR/STS with leave-at times.
    """
    try:
        return service.get_commute_to_home()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
