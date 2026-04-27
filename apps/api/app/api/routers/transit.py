from fastapi import APIRouter, HTTPException, Depends, Query
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

class UsageEventRequest(BaseModel):
    mode: str
    route_short_name: Optional[str] = None
    stop_id: Optional[str] = None
    stop_name: Optional[str] = None
    direction: Optional[str] = None
    source: str = "explicit"

class RoutineRequest(BaseModel):
    label: str
    mode: str
    route_short_name: Optional[str] = None
    stop_id: Optional[str] = None
    stop_name: Optional[str] = None
    dow_mask: int = 127
    hour_start: int = 0
    hour_end: int = 23
    confidence: float = 0.5

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


# ===== GTFS Static Discovery Endpoints =====

@router.get("/stops/search")
async def search_stops_by_name(
    q: str = Query(..., description="Search query (stop name)"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search stops by name using GTFS static data."""
    try:
        from app.services.gtfs_static import find_stops
        return {"query": q, "results": find_stops(q, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/near")
async def search_stops_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(400, ge=50, le=2000, description="Search radius in meters")
):
    """Find stops near a geographic location using GTFS static data."""
    try:
        from app.services.gtfs_static import find_stops_near
        return {"lat": lat, "lon": lon, "radius_m": radius, "results": find_stops_near(lat, lon, radius)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{short_name}")
async def get_route_details(short_name: str):
    """Get route details by short name (e.g. '27', '15A')."""
    try:
        from app.services.gtfs_static import resolve_route
        route = resolve_route(short_name)
        if not route:
            raise HTTPException(status_code=404, detail=f"Route '{short_name}' not found")
        return route
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{short_name}/stops")
async def get_route_stops(short_name: str):
    """Get stops served by a route (sampled from GTFS static trips)."""
    try:
        from app.services.gtfs_static import stops_served_by_route
        return {"route": short_name, "stops": stops_served_by_route(short_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes/{short_name}/status")
async def get_route_status(
    short_name: str,
    service: TransitService = Depends(get_transit_service)
):
    """Get real-time service alerts for a specific route."""
    try:
        return service.get_route_status(short_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Routine Learning Endpoints =====

@router.post("/events")
async def log_usage_event(event: UsageEventRequest):
    """
    Log a transit usage event (explicit user action or implicit view).
    Used to learn user's transit routines over time.
    """
    try:
        from app.services.routines import log_event
        event_id = log_event(
            mode=event.mode,
            route_short_name=event.route_short_name,
            stop_id=event.stop_id,
            stop_name=event.stop_name,
            direction=event.direction,
            source=event.source
        )
        return {"event_id": event_id, "status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routines")
async def get_routines():
    """List all learned transit routines."""
    try:
        from app.services.routines import list_routines
        return {"routines": list_routines()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routines")
async def create_routine_manual(routine: RoutineRequest):
    """Manually create a transit routine."""
    try:
        from app.services.routines import create_routine
        routine_id = create_routine(
            label=routine.label,
            mode=routine.mode,
            route_short_name=routine.route_short_name,
            stop_id=routine.stop_id,
            stop_name=routine.stop_name,
            dow_mask=routine.dow_mask,
            hour_start=routine.hour_start,
            hour_end=routine.hour_end,
            confidence=routine.confidence
        )
        return {"routine_id": routine_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/routines/{routine_id}")
async def delete_routine_by_id(routine_id: int):
    """Delete a transit routine."""
    try:
        from app.services.routines import delete_routine
        deleted = delete_routine(routine_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Routine not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routines/recompute")
async def recompute_routines_from_events(
    lookback_days: int = Query(60, ge=1, le=365),
    min_count: int = Query(3, ge=1, le=20)
):
    """
    Re-cluster usage_events into learned routines.
    Deletes old learned routines and creates new ones based on recent usage patterns.
    """
    try:
        from app.services.routines import recompute_routines
        result = recompute_routines(lookback_days=lookback_days, min_count=min_count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Proactive Advise Endpoints =====

@router.get("/advise/now")
async def advise_now(
    service: TransitService = Depends(get_transit_service)
):
    """
    Proactive advisor: get next relevant departures based on learned routines
    for the current time window. Returns approval-card shaped suggestions.
    """
    try:
        departures = service.next_relevant_departures()
        return {
            "timestamp": service._cache.get("now", (None, None))[0] or "now",
            "suggestions": departures
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advise/route/{short_name}")
async def advise_for_route(
    short_name: str,
    service: TransitService = Depends(get_transit_service)
):
    """
    Ad-hoc advisor: "Where's the {route}?" 
    Returns next 5 departures for this route across all user routine stops,
    or nearest stops if no routines exist.
    """
    try:
        from app.services.routines import list_routines
        from app.services.gtfs_static import find_stops
        
        routines = list_routines()
        relevant_stops = [r for r in routines if r.get("route", "").upper() == short_name.upper()]
        
        if not relevant_stops:
            # Fallback: search GTFS for common stops serving this route
            # (simplified - in production, would do a proper route→stop lookup)
            return {
                "route": short_name,
                "message": f"No routines found for route {short_name}. Try logging a journey first.",
                "departures": []
            }
        
        all_deps = []
        for routine in relevant_stops[:5]:  # Limit to 5 stops
            stop_id = routine["stop_id"]
            mode = routine["mode"]
            
            if mode == "luas":
                deps_data = service.get_luas_departures(stop_id)
            else:
                deps_data = service.get_bus_departures(stop_id, route_short_name=short_name)
            
            for dep in deps_data.get("departures", [])[:2]:
                if short_name.upper() in dep["route"].upper():
                    all_deps.append({
                        "stop_id": stop_id,
                        "stop_name": routine.get("stop_name", stop_id),
                        "route": dep["route"],
                        "destination": dep["destination"],
                        "due_minutes": dep["due_minutes"],
                        "mode": mode
                    })
        
        # Sort by due time
        all_deps.sort(key=lambda d: 0 if d["due_minutes"] == "Due" else (int(d["due_minutes"]) if str(d["due_minutes"]).isdigit() else 999))
        
        return {
            "route": short_name,
            "departures": all_deps[:5]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
