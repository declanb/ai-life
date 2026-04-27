"""
Transit Routine Learning & Storage

Learns the user's transit habits (which stops/routes/times they use) and
clusters them into "routines" for proactive departure suggestions.

Tables:
- usage_events: timestamped log of every journey the user views/logs
- routines: learned patterns (stop×route×dow×hour with confidence)

Storage: SQLite at apps/api/.data/ai_life.sqlite
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from collections import defaultdict


DATA_DIR = Path(os.getenv("AI_LIFE_DATA_DIR", Path(__file__).parent.parent.parent / ".data"))
DB_PATH = DATA_DIR / "ai_life.sqlite"

_db_conn: Optional[sqlite3.Connection] = None


def _get_db() -> sqlite3.Connection:
    """Get or create the SQLite connection."""
    global _db_conn
    if _db_conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _db_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
        _init_schema()
        _seed_from_user_stops()
    return _db_conn


def _init_schema():
    """Create tables if they don't exist."""
    db = _get_db() if _db_conn else sqlite3.connect(str(DB_PATH))
    cur = db.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            mode TEXT NOT NULL,
            route_short_name TEXT,
            stop_id TEXT,
            stop_name TEXT,
            direction TEXT,
            source TEXT DEFAULT 'explicit'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            mode TEXT NOT NULL,
            route_short_name TEXT,
            stop_id TEXT,
            stop_name TEXT,
            dow_mask INTEGER DEFAULT 127,
            hour_start INTEGER DEFAULT 0,
            hour_end INTEGER DEFAULT 23,
            confidence REAL DEFAULT 0.5,
            last_seen_utc TEXT
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON usage_events(ts_utc)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_routines_route ON routines(route_short_name)")
    
    db.commit()
    if _db_conn is None:
        db.close()


def _seed_from_user_stops():
    """
    One-time migration: seed routines from hardcoded user_stops.py data.
    Only runs if routines table is empty and a 'seeded' marker doesn't exist.
    """
    db = _get_db() if _db_conn else sqlite3.connect(str(DB_PATH))
    cur = db.cursor()
    
    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM routines WHERE label LIKE 'seed:%'")
    if cur.fetchone()[0] > 0:
        if _db_conn is None:
            db.close()
        return
    
    try:
        from app.data.user_stops import HOME_STOPS, WORK_STOPS, COMMUTE_ROUTES
        
        # Seed home bus stops
        for stop in HOME_STOPS:
            for route in stop.get("routes", []):
                cur.execute(
                    """
                    INSERT INTO routines (label, mode, route_short_name, stop_id, stop_name, 
                                          dow_mask, hour_start, hour_end, confidence, last_seen_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "seed:home_to_work",
                        stop.get("mode", "bus"),
                        route,
                        stop["id"],
                        stop["name"],
                        31,  # Mon-Fri (bits 0-4 set: 0b0011111 = 31)
                        7, 10,  # Morning commute window
                        0.5,
                        datetime.now(timezone.utc).isoformat()
                    )
                )
        
        # Seed work Luas stops
        for stop in WORK_STOPS:
            cur.execute(
                """
                INSERT INTO routines (label, mode, route_short_name, stop_id, stop_name,
                                      dow_mask, hour_start, hour_end, confidence, last_seen_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "seed:work_to_home",
                    stop.get("mode", "luas"),
                    f"Luas {stop.get('line', 'Green')}",
                    stop.get("abbrev", stop.get("id", "")),
                    stop["name"],
                    31,  # Mon-Fri
                    16, 19,  # Evening commute window
                    0.5,
                    datetime.now(timezone.utc).isoformat()
                )
            )
        
        db.commit()
        print("[Routines] Seeded initial routines from user_stops.py")
    
    except ImportError:
        pass  # user_stops doesn't exist yet, skip seeding
    
    if _db_conn is None:
        db.close()


def log_event(
    mode: str,
    route_short_name: Optional[str] = None,
    stop_id: Optional[str] = None,
    stop_name: Optional[str] = None,
    direction: Optional[str] = None,
    source: str = "explicit"
) -> int:
    """
    Log a transit usage event.
    Returns: event_id
    """
    db = _get_db()
    cur = db.cursor()
    
    cur.execute(
        """
        INSERT INTO usage_events (ts_utc, mode, route_short_name, stop_id, stop_name, direction, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            mode,
            route_short_name,
            stop_id,
            stop_name,
            direction,
            source
        )
    )
    
    db.commit()
    return cur.lastrowid


def list_routines() -> List[Dict]:
    """
    List all learned routines ordered by confidence DESC.
    Returns: [{"id", "label", "mode", "route", "stop_id", "stop_name", 
               "dow_mask", "hour_start", "hour_end", "confidence", "last_seen"}]
    """
    db = _get_db()
    cur = db.execute(
        """
        SELECT id, label, mode, route_short_name AS route, stop_id, stop_name,
               dow_mask, hour_start, hour_end, confidence, last_seen_utc AS last_seen
        FROM routines
        ORDER BY confidence DESC, last_seen_utc DESC
        """
    )
    return [dict(row) for row in cur.fetchall()]


def get_routine(routine_id: int) -> Optional[Dict]:
    """Get a single routine by ID."""
    db = _get_db()
    cur = db.execute("SELECT * FROM routines WHERE id = ?", (routine_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def delete_routine(routine_id: int) -> bool:
    """Delete a routine. Returns True if deleted, False if not found."""
    db = _get_db()
    cur = db.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
    db.commit()
    return cur.rowcount > 0


def create_routine(
    label: str,
    mode: str,
    route_short_name: Optional[str] = None,
    stop_id: Optional[str] = None,
    stop_name: Optional[str] = None,
    dow_mask: int = 127,
    hour_start: int = 0,
    hour_end: int = 23,
    confidence: float = 0.5
) -> int:
    """
    Manually create a routine.
    Returns: routine_id
    """
    db = _get_db()
    cur = db.cursor()
    
    cur.execute(
        """
        INSERT INTO routines (label, mode, route_short_name, stop_id, stop_name,
                              dow_mask, hour_start, hour_end, confidence, last_seen_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            label, mode, route_short_name, stop_id, stop_name,
            dow_mask, hour_start, hour_end, confidence,
            datetime.now(timezone.utc).isoformat()
        )
    )
    
    db.commit()
    return cur.lastrowid


def recompute_routines(lookback_days: int = 60, min_count: int = 3) -> Dict:
    """
    Re-cluster usage_events into routines.
    
    Algorithm:
    - Group events by (stop_id, route_short_name, direction, hour_bucket, day_of_week)
    - If group has ≥min_count events in last lookback_days, create/update a routine
    - Confidence = count / (count + 5)  [sigmoid-ish, caps at ~0.83 for frequent use]
    
    Returns: {"created": int, "updated": int, "deleted": int}
    """
    db = _get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    
    cur = db.execute(
        """
        SELECT mode, route_short_name, stop_id, stop_name, direction, ts_utc
        FROM usage_events
        WHERE ts_utc >= ?
        ORDER BY ts_utc
        """,
        (cutoff,)
    )
    
    events = [dict(row) for row in cur.fetchall()]
    
    # Cluster by (stop_id, route, direction, dow, hour_bucket)
    clusters = defaultdict(list)
    
    for evt in events:
        ts = datetime.fromisoformat(evt["ts_utc"])
        dow = ts.weekday()  # 0=Mon, 6=Sun
        hour = ts.hour
        hour_bucket = hour // 4  # 0-5 (0-3h, 4-7h, 8-11h, 12-15h, 16-19h, 20-23h)
        
        key = (
            evt["stop_id"],
            evt["route_short_name"],
            evt["direction"],
            dow,
            hour_bucket
        )
        clusters[key].append(evt)
    
    # Filter to frequent patterns
    frequent = {k: v for k, v in clusters.items() if len(v) >= min_count}
    
    # Clear old learned routines (keep seeds)
    db.execute("DELETE FROM routines WHERE label NOT LIKE 'seed:%'")
    
    created = 0
    for key, evts in frequent.items():
        stop_id, route, direction, dow, hour_bucket = key
        count = len(evts)
        confidence = count / (count + 5.0)
        
        mode = evts[0]["mode"]
        stop_name = evts[0]["stop_name"] or stop_id
        
        # DOW mask: single bit for this dow
        dow_mask = 1 << dow
        
        # Hour range from bucket
        hour_start = hour_bucket * 4
        hour_end = min(hour_start + 3, 23)
        
        last_seen = max(e["ts_utc"] for e in evts)
        
        label = f"learned:{mode}_{route or 'any'}_{stop_id}_{dow}"
        
        db.execute(
            """
            INSERT INTO routines (label, mode, route_short_name, stop_id, stop_name,
                                  dow_mask, hour_start, hour_end, confidence, last_seen_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (label, mode, route, stop_id, stop_name, dow_mask, hour_start, hour_end, confidence, last_seen)
        )
        created += 1
    
    db.commit()
    
    return {
        "created": created,
        "updated": 0,
        "deleted": 0,
        "events_analyzed": len(events),
        "clusters_found": len(clusters),
        "routines_learned": created
    }


def get_active_routines_for_time(dt: Optional[datetime] = None) -> List[Dict]:
    """
    Get routines that match the current (or given) time window.
    Checks: dow_mask bit for weekday, hour in [hour_start, hour_end].
    
    Returns: list of matching routines sorted by confidence DESC
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    dow = dt.weekday()  # 0=Mon, 6=Sun
    hour = dt.hour
    dow_bit = 1 << dow
    
    db = _get_db()
    cur = db.execute(
        """
        SELECT id, label, mode, route_short_name AS route, stop_id, stop_name,
               dow_mask, hour_start, hour_end, confidence, last_seen_utc AS last_seen
        FROM routines
        WHERE (dow_mask & ?) > 0
          AND hour_start <= ?
          AND hour_end >= ?
        ORDER BY confidence DESC
        """,
        (dow_bit, hour, hour)
    )
    
    return [dict(row) for row in cur.fetchall()]
