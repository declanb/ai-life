import httpx
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

class TransitService:
    def __init__(self):
        self.tfi_api_key = os.getenv("TFI_API_KEY")
        self.tfi_gtfsr_base = "https://api.nationaltransport.ie/gtfsr/v2"
        self.luas_base = "https://luasforecasts.rpa.ie/xml/get.ashx"
        self._cache: Dict[str, tuple[datetime, any]] = {}
        self.cache_ttl = timedelta(seconds=30)
        
    def _get_cached(self, key: str) -> Optional[any]:
        if key in self._cache:
            timestamp, data = self._cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: any):
        self._cache[key] = (datetime.now(), data)
    
    def get_bus_departures(self, stop_id: str, route_short_name: Optional[str] = None) -> Dict:
        """
        Get real-time Dublin Bus departures using TFI GTFS-Realtime API.
        
        Fetches TripUpdates feed, filters StopTimeUpdates for the given stop_id,
        returns sorted departures with route, destination, and due times.
        
        Args:
            stop_id: TFI stop ID
            route_short_name: Optional route filter (e.g. "27", "15A") for faster lookup
        """
        cache_key = f"bus_{stop_id}_{route_short_name or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        if not self.tfi_api_key:
            return {
                "stop_id": stop_id,
                "stop_name": f"Stop {stop_id}",
                "departures": [],
                "error": "TFI_API_KEY not configured"
            }
        
        url = f"{self.tfi_gtfsr_base}/TripUpdates"
        params = {"format": "json"}
        headers = {"x-api-key": self.tfi_api_key}
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                entities = data.get("entity", [])
                departures = []
                now = datetime.now(timezone.utc)
                
                # Build route_id → short_name map from GTFS static if available
                route_map = self._get_route_short_name_map()
                
                for entity in entities:
                    trip_update = entity.get("trip_update", {})
                    trip = trip_update.get("trip", {})
                    route_id = trip.get("route_id", "")
                    trip_id = trip.get("trip_id", "")
                    
                    # Resolve route short name
                    short_name = route_map.get(route_id, route_id.split("-")[-1] if "-" in route_id else route_id)
                    
                    # Apply route filter if specified
                    if route_short_name and short_name.upper() != route_short_name.upper():
                        continue
                    
                    stop_time_updates = trip_update.get("stop_time_update", [])
                    
                    for stu in stop_time_updates:
                        if stu.get("stop_id") == stop_id:
                            arrival = stu.get("arrival", {})
                            departure_info = stu.get("departure", {})
                            
                            arrival_time = arrival.get("time")
                            departure_time = departure_info.get("time")
                            scheduled_time = stu.get("schedule_relationship")
                            
                            target_timestamp = arrival_time or departure_time
                            if not target_timestamp:
                                continue
                            
                            try:
                                target_dt = datetime.fromtimestamp(int(target_timestamp), tz=timezone.utc)
                                due_seconds = (target_dt - now).total_seconds()
                                due_minutes = max(0, int(due_seconds / 60))
                                
                                headsign = trip.get("trip_headsign", trip_id)
                                
                                departure = {
                                    "route": short_name,
                                    "destination": headsign,
                                    "due_minutes": "Due" if due_minutes == 0 else str(due_minutes),
                                    "scheduled": target_dt.isoformat(),
                                    "realtime": target_dt.isoformat(),
                                    "mode": "bus"
                                }
                                departures.append(departure)
                            except (ValueError, TypeError):
                                continue
                
                departures.sort(key=lambda x: 0 if x["due_minutes"] == "Due" else int(x["due_minutes"]))
                
                result = {
                    "stop_id": stop_id,
                    "stop_name": f"Stop {stop_id}",
                    "departures": departures[:10]
                }
                
                self._set_cache(cache_key, result)
                return result
                
        except httpx.HTTPError as e:
            print(f"Error fetching TFI GTFS-R data for stop {stop_id}: {e}")
            return {
                "stop_id": stop_id,
                "stop_name": f"Stop {stop_id}",
                "departures": [],
                "error": f"TFI API error: {str(e)}"
            }
        except Exception as e:
            print(f"Unexpected error fetching bus data for stop {stop_id}: {e}")
            return {
                "stop_id": stop_id,
                "stop_name": f"Stop {stop_id}",
                "departures": [],
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_luas_departures(self, stop_abbrev: str) -> Dict:
        cache_key = f"luas_{stop_abbrev}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = self.luas_base
        params = {
            "action": "forecast",
            "stop": stop_abbrev,
            "encrypt": "false"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                
                stop_name = root.get("stopAbv", stop_abbrev)
                departures = []
                
                for direction in root.findall(".//direction"):
                    dir_name = direction.get("name", "")
                    
                    for tram in direction.findall("tram"):
                        due_minutes = tram.get("dueMins", "")
                        destination = tram.get("destination", dir_name)
                        
                        departure = {
                            "route": f"Luas {root.get('stopAbv', '')}",
                            "destination": destination,
                            "due_minutes": due_minutes,
                            "scheduled": "",
                            "realtime": due_minutes,
                            "mode": "luas"
                        }
                        departures.append(departure)
                
                result = {
                    "stop_id": stop_abbrev,
                    "stop_name": f"Luas {stop_name}",
                    "departures": sorted(departures, key=lambda x: int(x["due_minutes"]) if x["due_minutes"].isdigit() else 999)[:10]
                }
                
                self._set_cache(cache_key, result)
                return result
                
        except Exception as e:
            print(f"Error fetching Luas data for stop {stop_abbrev}: {e}")
            return {
                "stop_id": stop_abbrev,
                "stop_name": f"Luas {stop_abbrev}",
                "departures": [],
                "error": str(e)
            }
    
    def search_stops(self, query: str) -> List[Dict]:
        common_stops = [
            {"stop_id": "334", "name": "Phibsborough, stop 334", "type": "bus"},
            {"stop_id": "273", "name": "O'Connell Street Upper, stop 273", "type": "bus"},
            {"stop_id": "751", "name": "Trinity College, stop 751", "type": "bus"},
            {"stop_id": "4534", "name": "Dublin Airport, stop 4534", "type": "bus"},
            {"stop_id": "JER", "name": "Jervis (Luas Red Line)", "type": "luas"},
            {"stop_id": "STS", "name": "St. Stephen's Green (Luas Green Line)", "type": "luas"},
            {"stop_id": "TAL", "name": "Tallaght (Luas Red Line)", "type": "luas"},
            {"stop_id": "CON", "name": "Connolly (Luas Red Line)", "type": "luas"},
            {"stop_id": "BRI", "name": "Broombridge (Luas Green Line)", "type": "luas"},
        ]
        
        query_lower = query.lower()
        results = [s for s in common_stops if query_lower in s["name"].lower()]
        return results[:10]
    
    def suggest_commute(
        self, 
        origin_stop: str, 
        route: Optional[str], 
        destination: Optional[str],
        walk_minutes: int = 5,
        mode: str = "bus"
    ) -> Dict:
        if mode == "luas":
            departures_data = self.get_luas_departures(origin_stop)
        else:
            departures_data = self.get_bus_departures(origin_stop)
        
        departures = departures_data.get("departures", [])
        
        if route:
            departures = [d for d in departures if route.lower() in d["route"].lower()]
        if destination:
            departures = [d for d in departures if destination.lower() in d["destination"].lower()]
        
        if not departures:
            return {
                "title": "No upcoming departures",
                "body": f"No matching services found from {departures_data.get('stop_name', origin_stop)}",
                "action_at": None,
                "cta": None
            }
        
        next_departure = departures[0]
        due_str = next_departure["due_minutes"]
        
        if due_str.lower() == "due":
            due_minutes = 0
        elif due_str.isdigit():
            due_minutes = int(due_str)
        else:
            due_minutes = 999
        
        leave_in = max(0, due_minutes - walk_minutes)
        
        if leave_in == 0:
            leave_msg = "Leave NOW"
            action_at = datetime.now().isoformat()
        else:
            leave_time = datetime.now() + timedelta(minutes=leave_in)
            leave_msg = f"Leave in {leave_in} min"
            action_at = leave_time.isoformat()
        
        return {
            "title": f"{next_departure['route']} to {next_departure['destination']}",
            "body": f"Departs in {due_str} min. {leave_msg} ({walk_minutes} min walk).",
            "action_at": action_at,
            "cta": "Dismiss"
        }
    
    def get_commute_to_work(self) -> Dict:
        """
        Get personalised commute options from Coolock home to Harcourt St work.
        Returns top options from home bus stops (15/15A/15B) with leave-at times.
        """
        from app.data.user_stops import HOME_STOPS, COMMUTE_ROUTES, DEFAULT_WALK_MINUTES
        
        walk_minutes = DEFAULT_WALK_MINUTES["home"]
        all_options = []
        
        for stop in HOME_STOPS:
            departures_data = self.get_bus_departures(stop["id"])
            departures = departures_data.get("departures", [])
            
            for dep in departures:
                route = dep["route"]
                if route in COMMUTE_ROUTES or any(r in route for r in COMMUTE_ROUTES):
                    due_str = dep["due_minutes"]
                    
                    if due_str.lower() == "due":
                        due_minutes = 0
                    elif due_str.isdigit():
                        due_minutes = int(due_str)
                    else:
                        continue
                    
                    leave_in = max(0, due_minutes - walk_minutes - 1)
                    leave_at = datetime.now() + timedelta(minutes=leave_in)
                    
                    all_options.append({
                        "stop_name": stop["name"],
                        "stop_id": stop["id"],
                        "route": route,
                        "destination": dep["destination"],
                        "due_minutes": due_minutes,
                        "due_str": due_str,
                        "leave_at": leave_at.strftime("%H:%M"),
                        "leave_in_minutes": leave_in,
                        "walk_minutes": walk_minutes,
                        "mode": "bus"
                    })
        
        all_options.sort(key=lambda x: x["due_minutes"])
        top_options = all_options[:3]
        
        recommendation = None
        if top_options:
            best = top_options[0]
            if best["leave_in_minutes"] <= 2:
                urgency = "Leave NOW!"
            elif best["leave_in_minutes"] <= 5:
                urgency = f"Leave in {best['leave_in_minutes']} min"
            else:
                urgency = f"Leave at {best['leave_at']}"
            
            recommendation = f"{urgency} for {best['route']} from {best['stop_name']}"
        
        return {
            "direction": "to_work",
            "origin": "Coolock (Home)",
            "destination": "Harcourt St (Work)",
            "options": top_options,
            "recommendation": recommendation,
            "walk_minutes": walk_minutes
        }
    
    def get_commute_to_home(self) -> Dict:
        """
        Get personalised commute options from Harcourt St work to Coolock home.
        Returns top options from work Luas stops (HAR/STS) with leave-at times.
        """
        from app.data.user_stops import WORK_STOPS, DEFAULT_WALK_MINUTES
        
        walk_minutes = DEFAULT_WALK_MINUTES["work"]
        all_options = []
        
        for stop in WORK_STOPS:
            if stop["mode"] == "luas":
                departures_data = self.get_luas_departures(stop["abbrev"])
                departures = departures_data.get("departures", [])
                
                for dep in departures:
                    dest = dep["destination"].lower()
                    if "brides glen" in dest or "sandyford" in dest or "broombridge" in dest:
                        continue
                    
                    due_str = dep["due_minutes"]
                    
                    if due_str.lower() == "due":
                        due_minutes = 0
                    elif due_str.isdigit():
                        due_minutes = int(due_str)
                    else:
                        continue
                    
                    leave_in = max(0, due_minutes - walk_minutes - 1)
                    leave_at = datetime.now() + timedelta(minutes=leave_in)
                    
                    all_options.append({
                        "stop_name": stop["name"],
                        "stop_id": stop["abbrev"],
                        "route": f"Luas {stop['line']}",
                        "destination": dep["destination"],
                        "due_minutes": due_minutes,
                        "due_str": due_str,
                        "leave_at": leave_at.strftime("%H:%M"),
                        "leave_in_minutes": leave_in,
                        "walk_minutes": walk_minutes,
                        "mode": "luas"
                    })
        
        all_options.sort(key=lambda x: x["due_minutes"])
        top_options = all_options[:3]
        
        recommendation = None
        if top_options:
            best = top_options[0]
            if best["leave_in_minutes"] <= 2:
                urgency = "Leave NOW!"
            elif best["leave_in_minutes"] <= 5:
                urgency = f"Leave in {best['leave_in_minutes']} min"
            else:
                urgency = f"Leave at {best['leave_at']}"
            
            recommendation = f"{urgency} for {best['route']} from {best['stop_name']}"
        
        return {
            "direction": "to_home",
            "origin": "Harcourt St (Work)",
            "destination": "Coolock (Home)",
            "options": top_options,
            "recommendation": recommendation,
            "walk_minutes": walk_minutes
        }
    
    def _get_route_short_name_map(self) -> Dict[str, str]:
        """
        Build route_id → short_name map from GTFS static data.
        Cached for 5 minutes.
        """
        cache_key = "route_map"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            from app.services.gtfs_static import _get_db
            db = _get_db()
            cur = db.execute("SELECT route_id, route_short_name FROM routes")
            route_map = {row[0]: row[1] for row in cur.fetchall() if row[1]}
            self._set_cache(cache_key, route_map)
            return route_map
        except Exception as e:
            print(f"[TransitService] Could not load route map: {e}")
            return {}
    
    def get_route_status(self, route_short_name: str) -> Dict:
        """
        Check GTFS-R ServiceAlerts for disruptions on a specific route.
        Returns: {"route", "alerts": [{"header", "description", "effect"}]}
        """
        if not self.tfi_api_key:
            return {"route": route_short_name, "alerts": [], "error": "TFI_API_KEY not configured"}
        
        url = f"{self.tfi_gtfsr_base}/ServiceAlerts"
        params = {"format": "json"}
        headers = {"x-api-key": self.tfi_api_key}
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                alerts = []
                route_map = self._get_route_short_name_map()
                
                for entity in data.get("entity", []):
                    alert = entity.get("alert", {})
                    informed_entities = alert.get("informed_entity", [])
                    
                    for ie in informed_entities:
                        route_id = ie.get("route_id", "")
                        short_name = route_map.get(route_id, route_id.split("-")[-1] if "-" in route_id else route_id)
                        
                        if short_name.upper() == route_short_name.upper():
                            header_text = alert.get("header_text", {}).get("translation", [{}])[0].get("text", "Alert")
                            desc_text = alert.get("description_text", {}).get("translation", [{}])[0].get("text", "")
                            effect = alert.get("effect", "UNKNOWN_EFFECT")
                            
                            alerts.append({
                                "header": header_text,
                                "description": desc_text,
                                "effect": effect
                            })
                            break
                
                return {"route": route_short_name, "alerts": alerts}
        
        except Exception as e:
            print(f"[TransitService] Error fetching alerts for route {route_short_name}: {e}")
            return {"route": route_short_name, "alerts": [], "error": str(e)}
    
    def next_relevant_departures(self, now_utc: Optional[datetime] = None, window_minutes: int = 30) -> List[Dict]:
        """
        Proactive advisor: get next departures for all active routines in the current time window.
        
        Returns approval-card shaped dicts:
        [{"title", "body", "action_at", "leave_at", "route", "stop_id", "due_minutes", "confidence"}]
        
        Sorted by: urgency (soonest leave_at first), then confidence DESC.
        """
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)
        
        from app.services.routines import get_active_routines_for_time
        
        active_routines = get_active_routines_for_time(now_utc)
        if not active_routines:
            return []
        
        candidates = []
        
        for routine in active_routines:
            mode = routine["mode"]
            stop_id = routine["stop_id"]
            route = routine.get("route")
            stop_name = routine.get("stop_name", stop_id)
            confidence = routine.get("confidence", 0.5)
            
            # Fetch live departures
            if mode == "luas":
                deps_data = self.get_luas_departures(stop_id)
            else:
                deps_data = self.get_bus_departures(stop_id, route_short_name=route)
            
            departures = deps_data.get("departures", [])
            
            # Filter by route if specified in routine
            if route:
                departures = [d for d in departures if route.upper() in d["route"].upper()]
            
            # Take next 2 departures within window
            for dep in departures[:2]:
                due_str = dep["due_minutes"]
                
                if due_str == "Due":
                    due_minutes = 0
                elif due_str.isdigit():
                    due_minutes = int(due_str)
                else:
                    continue
                
                if due_minutes > window_minutes:
                    continue
                
                # Assume 5 min walk (could be enhanced with routine-specific walk time)
                walk_minutes = 5
                leave_in = max(0, due_minutes - walk_minutes)
                leave_at = now_utc + timedelta(minutes=leave_in)
                
                title = f"{dep['route']} to {dep['destination']} in {due_minutes} min"
                body = f"Leave by {leave_at.strftime('%H:%M')} — {walk_minutes} min walk from {stop_name}"
                
                candidates.append({
                    "title": title,
                    "body": body,
                    "action_at": leave_at.isoformat(),
                    "leave_at": leave_at.isoformat(),
                    "route": dep["route"],
                    "stop_id": stop_id,
                    "stop_name": stop_name,
                    "due_minutes": due_minutes,
                    "confidence": confidence,
                    "mode": mode
                })
        
        # Sort: soonest leave_at first, then highest confidence
        candidates.sort(key=lambda c: (c["leave_at"], -c["confidence"]))
        return candidates
