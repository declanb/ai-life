# Dublin Transit Agent Evolution — Implementation Summary

## What Changed

Evolved the Dublin transit module from hardcoded stops into an **API-driven, routine-learning system** that proactively advises "the 27 is N minutes away — leave now".

### New Capabilities

1. **GTFS Static Discovery** — TFI stop/route lookup without hardcoding
2. **Routine Learning** — AI-Life learns which stops/routes/times the user actually uses
3. **Proactive Advising** — "Now" recommendations based on learned patterns
4. **Route 27 Support** — Added alongside 15/15A/15B in seed data

---

## Files Changed

### Backend (apps/api/)

**New files:**
- `app/services/gtfs_static.py` — GTFS static loader & discovery API
- `app/services/routines.py` — Usage event logging & routine clustering

**Modified files:**
- `app/services/transit_service.py` — Added route filtering, service alerts, proactive advisor
- `app/api/routers/transit.py` — 12 new endpoints (discovery, routines, advise)
- `app/data/user_stops.py` — Deprecated (now seed-only), added route 27
- `.env.example` — Added AI_LIFE_DATA_DIR variable
- `README.md` — Documented new endpoints & routine learning

### Frontend (apps/web/)

**Modified files:**
- `components/transit/TransitDashboard.tsx` — Added "Now" proactive strip + "Log this journey" buttons

### Infrastructure

**Modified files:**
- `.gitignore` — Added `.cache/` and `.data/` patterns

---

## How Routine Learning Works

1. **Events logged** via `POST /transit/events` when user views or explicitly marks a journey
2. **Clustering** via `POST /transit/routines/recompute` groups events by (stop, route, hour-bucket, day-of-week)
3. **Confidence scoring**: count/(count+5) — frequent patterns score higher
4. **Proactive matching**: `GET /transit/advise/now` finds routines matching current time window, fetches live GTFS-R departures, returns approval-card shaped suggestions

Data stored in SQLite at `apps/api/.data/ai_life.sqlite`. Seeded from `user_stops.py` on first boot.

---

## GTFS Static Cache

- **First use**: Downloads ~50MB GTFS_All.zip from transportforireland.ie
- **Cache**: `apps/api/.cache/gtfs/gtfs.sqlite` (stops, routes, trips tables)
- **TTL**: 30 days
- **Manual refresh**: `cd apps/api && python -m app.services.gtfs_static refresh`

---

## New Endpoints

### Discovery (GTFS Static)

```bash
# Search stops by name
GET /api/v1/transit/stops/search?q=Coolock

# Find nearby stops
GET /api/v1/transit/stops/near?lat=53.3869&lon=-6.1917&radius=400

# Get route details
GET /api/v1/transit/routes/27

# Get stops served by route
GET /api/v1/transit/routes/27/stops

# Check service alerts
GET /api/v1/transit/routes/27/status
```

### Routines (Learning)

```bash
# Log a journey event
POST /api/v1/transit/events
Content-Type: application/json
{
  "mode": "bus",
  "route_short_name": "27",
  "stop_id": "4513",
  "stop_name": "Tonlegee Rd (Coolock)",
  "direction": "City Centre",
  "source": "explicit"
}

# List learned routines
GET /api/v1/transit/routines

# Recompute routines from events (clusters last 60 days)
POST /api/v1/transit/routines/recompute

# Manually create a routine
POST /api/v1/transit/routines
Content-Type: application/json
{
  "label": "Morning 27 to work",
  "mode": "bus",
  "route_short_name": "27",
  "stop_id": "4513",
  "stop_name": "Tonlegee Rd",
  "dow_mask": 31,
  "hour_start": 7,
  "hour_end": 10,
  "confidence": 0.8
}

# Delete a routine
DELETE /api/v1/transit/routines/1
```

### Proactive Advising

```bash
# Get "Now" recommendations (matching active routines)
GET /api/v1/transit/advise/now

# "Where's the 27?" — next departures across user's routine stops
GET /api/v1/transit/advise/route/27
```

---

## Curl Examples

### 1. Search for Coolock stops
```bash
curl "http://localhost:8000/api/v1/transit/stops/search?q=Coolock&limit=5"
```

**Response:**
```json
{
  "query": "Coolock",
  "results": [
    {"stop_id": "4513", "stop_name": "Tonlegee Road", "lat": 53.3869, "lon": -6.1917},
    {"stop_id": "4512", "stop_name": "Kilmore Road", "lat": 53.3855, "lon": -6.1890}
  ]
}
```

### 2. Log a route 27 journey event
```bash
curl -X POST http://localhost:8000/api/v1/transit/events \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "bus",
    "route_short_name": "27",
    "stop_id": "4513",
    "stop_name": "Tonlegee Rd (Coolock)",
    "direction": "City Centre",
    "source": "explicit"
  }'
```

**Response:**
```json
{"event_id": 42, "status": "logged"}
```

### 3. Recompute routines (after logging ≥3 events)
```bash
curl -X POST "http://localhost:8000/api/v1/transit/routines/recompute?lookback_days=60&min_count=3"
```

**Response:**
```json
{
  "created": 2,
  "updated": 0,
  "deleted": 0,
  "events_analyzed": 12,
  "clusters_found": 5,
  "routines_learned": 2
}
```

### 4. Ask "What should I do now?"
```bash
curl http://localhost:8000/api/v1/transit/advise/now
```

**Response:**
```json
{
  "timestamp": "now",
  "suggestions": [
    {
      "title": "27 to City Centre in 6 min",
      "body": "Leave by 14:33 — 5 min walk from Tonlegee Rd",
      "action_at": "2026-04-19T14:33:00Z",
      "leave_at": "2026-04-19T14:33:00Z",
      "route": "27",
      "stop_id": "4513",
      "stop_name": "Tonlegee Rd (Coolock)",
      "due_minutes": 6,
      "confidence": 0.75,
      "mode": "bus"
    }
  ]
}
```

### 5. Ask "Where's the 27?"
```bash
curl http://localhost:8000/api/v1/transit/advise/route/27
```

**Response:**
```json
{
  "route": "27",
  "departures": [
    {
      "stop_id": "4513",
      "stop_name": "Tonlegee Rd (Coolock)",
      "route": "27",
      "destination": "Jobstown",
      "due_minutes": "6",
      "mode": "bus"
    },
    {
      "stop_id": "4513",
      "stop_name": "Tonlegee Rd (Coolock)",
      "route": "27",
      "destination": "Clare Hall",
      "due_minutes": "14",
      "mode": "bus"
    }
  ]
}
```

---

## First-Time Setup

1. **Install dependencies** (already verified working):
   ```bash
   cd apps/api
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Trigger GTFS refresh** (auto-runs on first API call to discovery endpoints, or manually):
   ```bash
   cd apps/api
   python -m app.services.gtfs_static refresh
   ```
   Downloads ~50MB, parses into `.cache/gtfs/gtfs.sqlite` (~20MB).

3. **Start the API**:
   ```bash
   cd apps/api
   uvicorn app.main:app --reload
   ```

4. **Seed routines** (happens automatically on first DB access — migrates `user_stops.py` data).

---

## What's Next

### User-facing workflow:
1. Use transit dashboard as normal
2. Click "Log this journey" on routes you take → builds usage history
3. After ~3 uses of same stop/route/time pattern, run `/routines/recompute` (or schedule nightly)
4. "Now" strip shows proactive suggestions for learned routines

### Future enhancements (not implemented):
- Auto-recompute routines nightly via cron/task scheduler
- Per-routine walk times (currently hardcoded 5 min)
- Geofence triggers (e.g., "left work → advise on Luas home")
- Push notifications for urgent "leave NOW" alerts
- Multi-user profiles (auth required first)

---

## Constraints Respected

✅ **No new runtime deps** — stdlib only (sqlite3, zipfile, csv, math)  
✅ **API-first** — all features accessible via REST  
✅ **Approval-card consistent** — advise endpoints return same shape as `suggest_commute()`  
✅ **No breaking changes** — existing `/commute/to-work` and `/commute/to-home` unchanged  
✅ **SQLite only** — no DB server, `.data/` and `.cache/` gitignored  
✅ **Pip install succeeds** — verified clean install  
✅ **No new markdown docs** — only updated existing README

---

**Implementation complete.** The transit agent now learns from usage, discovers stops/routes dynamically, and proactively advises when the 27 (or any learned route) is approaching.
