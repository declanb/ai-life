"""
GTFS Static Data Loader for TFI (Transport for Ireland)

Downloads and caches the TFI GTFS static dataset locally:
- Source: https://www.transportforireland.ie/transitData/Data/GTFS_All.zip
- Cache: apps/api/.cache/gtfs/ (zip + parsed SQLite DB)
- Refresh: TTL 30 days, or via CLI `python -m app.services.gtfs_static refresh`

Provides stop/route lookup functions without hitting the network at query time.
"""

import os
import sqlite3
import zipfile
import csv
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

GTFS_ZIP_URL = "https://www.transportforireland.ie/transitData/Data/GTFS_All.zip"
CACHE_DIR = Path(__file__).parent.parent.parent / ".cache" / "gtfs"
DB_PATH = CACHE_DIR / "gtfs.sqlite"
ZIP_PATH = CACHE_DIR / "GTFS_All.zip"
CACHE_TTL_DAYS = 30

_db_conn: Optional[sqlite3.Connection] = None


def _get_db() -> sqlite3.Connection:
    """Get or create the SQLite connection."""
    global _db_conn
    if _db_conn is None:
        ensure_loaded()
        _db_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km using haversine formula."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def ensure_loaded(force_refresh: bool = False):
    """Download and parse GTFS static data if not cached or stale."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    needs_refresh = force_refresh or not DB_PATH.exists()
    
    if DB_PATH.exists() and not force_refresh:
        modified_time = datetime.fromtimestamp(DB_PATH.stat().st_mtime)
        age_days = (datetime.now() - modified_time).days
        if age_days > CACHE_TTL_DAYS:
            print(f"[GTFS] Cache is {age_days} days old (TTL: {CACHE_TTL_DAYS}), refreshing...")
            needs_refresh = True
    
    if not needs_refresh:
        return
    
    print(f"[GTFS] Downloading {GTFS_ZIP_URL}...")
    try:
        with httpx.stream("GET", GTFS_ZIP_URL, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            with open(ZIP_PATH, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        print(f"[GTFS] Downloaded {ZIP_PATH.stat().st_size / (1024*1024):.1f} MB")
    except Exception as e:
        print(f"[GTFS] Download failed: {e}")
        if DB_PATH.exists():
            print("[GTFS] Using stale cache")
            return
        raise
    
    print("[GTFS] Parsing into SQLite...")
    _parse_gtfs_to_sqlite()
    print(f"[GTFS] Ready: {DB_PATH}")


def _parse_gtfs_to_sqlite():
    """Extract GTFS txt files from zip and load into SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT,
            stop_lat REAL,
            stop_lon REAL,
            location_type INTEGER,
            parent_station TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY,
            route_short_name TEXT,
            route_long_name TEXT,
            route_type INTEGER,
            agency_id TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            route_id TEXT,
            trip_headsign TEXT,
            direction_id INTEGER,
            shape_id TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stop_times (
            trip_id TEXT,
            stop_id TEXT,
            stop_sequence INTEGER,
            arrival_time TEXT,
            departure_time TEXT
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stops_name ON stops(stop_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_short ON routes(route_short_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trips_route ON trips(route_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stop_times_stop ON stop_times(stop_id)")
    
    conn.commit()
    
    # Parse from zip
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        # Stops
        if "stops.txt" in zf.namelist():
            with zf.open("stops.txt") as f:
                reader = csv.DictReader((line.decode('utf-8-sig') for line in f))
                stops_data = [
                    (
                        row.get("stop_id", ""),
                        row.get("stop_name", ""),
                        float(row.get("stop_lat", 0) or 0),
                        float(row.get("stop_lon", 0) or 0),
                        int(row.get("location_type", 0) or 0),
                        row.get("parent_station", "")
                    )
                    for row in reader
                ]
                cur.executemany(
                    "INSERT OR REPLACE INTO stops VALUES (?, ?, ?, ?, ?, ?)",
                    stops_data
                )
                print(f"  Loaded {len(stops_data)} stops")
        
        # Routes
        if "routes.txt" in zf.namelist():
            with zf.open("routes.txt") as f:
                reader = csv.DictReader((line.decode('utf-8-sig') for line in f))
                routes_data = [
                    (
                        row.get("route_id", ""),
                        row.get("route_short_name", ""),
                        row.get("route_long_name", ""),
                        int(row.get("route_type", 3) or 3),
                        row.get("agency_id", "")
                    )
                    for row in reader
                ]
                cur.executemany(
                    "INSERT OR REPLACE INTO routes VALUES (?, ?, ?, ?, ?)",
                    routes_data
                )
                print(f"  Loaded {len(routes_data)} routes")
        
        # Trips (limited insert to avoid huge table — only store headsigns)
        if "trips.txt" in zf.namelist():
            with zf.open("trips.txt") as f:
                reader = csv.DictReader((line.decode('utf-8-sig') for line in f))
                trips_data = [
                    (
                        row.get("trip_id", ""),
                        row.get("route_id", ""),
                        row.get("trip_headsign", ""),
                        int(row.get("direction_id", 0) or 0),
                        row.get("shape_id", "")
                    )
                    for row in reader
                ]
                # Sample: only keep unique route_id + headsign combos for discovery
                seen = set()
                unique_trips = []
                for trip in trips_data:
                    key = (trip[1], trip[2])  # route_id, headsign
                    if key not in seen:
                        seen.add(key)
                        unique_trips.append(trip)
                
                cur.executemany(
                    "INSERT OR REPLACE INTO trips VALUES (?, ?, ?, ?, ?)",
                    unique_trips[:10000]  # Limit to 10k representative trips
                )
                print(f"  Loaded {len(unique_trips)} unique trip headsigns (sampled from {len(trips_data)})")
        
        # Stop times — skip for now (huge table, not needed for discovery)
        # We rely on GTFS-R for live times, GTFS-static is only for stop/route metadata
    
    conn.commit()
    conn.close()


def find_stops(query: str, limit: int = 20) -> List[Dict]:
    """
    Search stops by name (case-insensitive LIKE).
    Returns: [{"stop_id", "stop_name", "lat", "lon"}]
    """
    db = _get_db()
    cur = db.execute(
        """
        SELECT stop_id, stop_name, stop_lat AS lat, stop_lon AS lon
        FROM stops
        WHERE stop_name LIKE ? AND location_type = 0
        ORDER BY stop_name
        LIMIT ?
        """,
        (f"%{query}%", limit)
    )
    return [dict(row) for row in cur.fetchall()]


def find_stops_near(lat: float, lon: float, radius_m: int = 400, limit: int = 20) -> List[Dict]:
    """
    Find stops within radius_m meters of (lat, lon).
    Returns: [{"stop_id", "stop_name", "lat", "lon", "distance_m"}]
    """
    db = _get_db()
    cur = db.execute(
        "SELECT stop_id, stop_name, stop_lat AS lat, stop_lon AS lon FROM stops WHERE location_type = 0"
    )
    
    candidates = []
    for row in cur.fetchall():
        stop_lat = row["lat"]
        stop_lon = row["lon"]
        dist_km = _haversine_km(lat, lon, stop_lat, stop_lon)
        dist_m = dist_km * 1000
        if dist_m <= radius_m:
            candidates.append({
                "stop_id": row["stop_id"],
                "stop_name": row["stop_name"],
                "lat": stop_lat,
                "lon": stop_lon,
                "distance_m": int(dist_m)
            })
    
    candidates.sort(key=lambda s: s["distance_m"])
    return candidates[:limit]


def resolve_route(short_name: str) -> Optional[Dict]:
    """
    Resolve route short_name (e.g. "27", "15A") to full route details.
    Returns: {"route_id", "short_name", "long_name", "type", "agency"} or None
    """
    db = _get_db()
    cur = db.execute(
        """
        SELECT route_id, route_short_name AS short_name, route_long_name AS long_name,
               route_type AS type, agency_id AS agency
        FROM routes
        WHERE route_short_name = ? COLLATE NOCASE
        LIMIT 1
        """,
        (short_name,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def stops_served_by_route(short_name: str) -> List[Dict]:
    """
    Get all stops served by a route (based on trips in GTFS static).
    Returns: [{"stop_id", "stop_name", "direction_id", "headsign"}]
    
    Note: This is sampled data from trips table. For full accuracy,
    would need to join stop_times, but we keep it lightweight.
    """
    route = resolve_route(short_name)
    if not route:
        return []
    
    route_id = route["route_id"]
    db = _get_db()
    
    # Get representative trips for this route
    cur = db.execute(
        """
        SELECT DISTINCT trip_headsign, direction_id
        FROM trips
        WHERE route_id = ?
        """,
        (route_id,)
    )
    
    trips = [dict(row) for row in cur.fetchall()]
    
    # For simplicity, return the route headsigns; actual stop_id linkage
    # would require stop_times join (not loaded). Caller should use GTFS-R
    # for live stop×route associations.
    return [
        {
            "stop_id": None,  # Placeholder — use GTFS-R for actual stop IDs
            "stop_name": trip["trip_headsign"],
            "direction_id": trip["direction_id"],
            "headsign": trip["trip_headsign"]
        }
        for trip in trips
    ]


def refresh():
    """CLI entrypoint: force refresh GTFS cache."""
    print("[GTFS] Force refresh requested")
    ensure_loaded(force_refresh=True)
    print("[GTFS] Refresh complete")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh()
    else:
        ensure_loaded()
        print(f"[GTFS] Cache ready at {DB_PATH}")
        print(f"\nExample: find_stops('Coolock') =>")
        results = find_stops("Coolock", limit=5)
        for r in results:
            print(f"  {r['stop_id']}: {r['stop_name']}")
