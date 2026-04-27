# API Service

FastAPI backend for ai-life personal assistant.

## Environment Variables

Create a `.env` file in the `apps/api/` directory:

```bash
# Required for Vercel integration
VERCEL_TOKEN=your_vercel_token_here
VERCEL_TEAM_ID=your_team_id_here

# Required for Dublin Bus real-time data via TFI GTFS-Realtime API
# Register at https://developer.nationaltransport.ie/ and subscribe to GTFS-R API
# API key activates after ~15 minutes once subscription is confirmed
TFI_API_KEY=your_tfi_api_key_here
```

## Endpoints

## Google Calendar (Travel Sync) setup

1. Place your Google OAuth Desktop client JSON at:

   ```
   apps/api/.secrets/google_oauth_client.json
   ```

   (This folder is gitignored.)

2. Install deps and run the one-time consent flow:

   ```sh
   cd apps/api
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python -m app.cli.google_auth
   ```

   Browser opens, you grant the `calendar` scope, token is written to
   `apps/api/.secrets/google_oauth_token.json`. Keep the OAuth consent
   screen **Published** (not Testing) so the refresh token doesn't expire.

3. Run the API:

   ```sh
   uvicorn app.main:app --reload
   ```

## Trips API (vertical slice 1 — Travel Sync)

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/v1/trips` | List pending + applied trip approvals |
| POST   | `/api/v1/trips` | Register a new trip → PENDING approval card |
| GET    | `/api/v1/trips/{id}` | Fetch one approval |
| POST   | `/api/v1/trips/{id}/approve` | Write events to Google Calendar |
| POST   | `/api/v1/trips/{id}/reject` | Dismiss without writing |
| DELETE | `/api/v1/trips/{id}` | Revert (delete events from calendar) |

Events go to a dedicated secondary calendar **"AI-Life — Travel"**,
auto-created on first apply. Deleting that calendar in Google is full undo.

### Smoke test

```sh
curl -X POST http://localhost:8000/api/v1/trips \
  -H 'content-type: application/json' \
  -d '{
    "id": "demo-001",
    "title": "London → New York",
    "start_local": "2026-04-28T07:00:00",
    "end_local":   "2026-04-30T22:00:00",
    "tz": "Europe/London",
    "source": "manual",
    "flights": [{
      "carrier": "BA", "flight_number": "117",
      "origin_iata": "LHR", "destination_iata": "JFK",
      "depart_local": "2026-04-28T08:30:00",
      "arrive_local": "2026-04-28T11:30:00",
      "depart_tz": "Europe/London", "arrive_tz": "America/New_York"
    }]
  }'

curl -X POST http://localhost:8000/api/v1/trips/demo-001/approve
```

### Transit

Real-time Dublin Bus (via TFI GTFS-R) and Luas departures with **routine learning** and **proactive advising**.

#### How Routine Learning Works

The transit agent learns your habits over time:
1. **Log events** (explicit or implicit) via `POST /transit/events` when you view or use a route
2. **Recompute routines** via `POST /transit/routines/recompute` to cluster usage into patterns (stop×route×time-of-day×day-of-week)
3. **Proactive suggestions** via `GET /transit/advise/now` returns "the 27 is N minutes away — leave now" cards based on active routines

Routines are stored in SQLite (`apps/api/.data/ai_life.sqlite`) and seeded from `user_stops.py` on first boot.

#### GTFS Static Cache

Stop and route discovery uses the TFI GTFS static dataset:
- **First use**: downloads ~50MB zip from transportforireland.ie, parses into SQLite
- **Cache location**: `apps/api/.cache/gtfs/`
- **Refresh**: `cd apps/api && python -m app.services.gtfs_static refresh` (or auto-refreshes after 30 days)

#### Endpoints

**Personalised commute (legacy — uses hardcoded stops):**
- `GET /api/v1/transit/commute/to-work` - Coolock → Harcourt St (15/15A/15B/27 buses)
- `GET /api/v1/transit/commute/to-home` - Harcourt St → Coolock (Luas Green Line from HAR/STS)

**Discovery (GTFS static):**
- `GET /api/v1/transit/stops/search?q=<name>` - Search stops by name
- `GET /api/v1/transit/stops/near?lat=<lat>&lon=<lon>&radius=<meters>` - Find nearby stops
- `GET /api/v1/transit/routes/{short_name}` - Get route details (e.g. /routes/27)
- `GET /api/v1/transit/routes/{short_name}/stops` - Stops served by route
- `GET /api/v1/transit/routes/{short_name}/status` - Live service alerts

**Routines (learning):**
- `POST /api/v1/transit/events` - Log a journey event (implicit/explicit)
- `GET /api/v1/transit/routines` - List learned routines
- `POST /api/v1/transit/routines` - Manually create a routine
- `DELETE /api/v1/transit/routines/{id}` - Delete a routine
- `POST /api/v1/transit/routines/recompute` - Re-cluster events into routines

**Proactive advising:**
- `GET /api/v1/transit/advise/now` - Next relevant departures for current time window
- `GET /api/v1/transit/advise/route/{short_name}` - "Where's the 27?" — next departures across user's routine stops

**Generic:**
- `GET /api/v1/transit/bus/stop/{stop_id}` - Real-time Dublin Bus departures from any stop
- `GET /api/v1/transit/luas/stop/{abbrev}` - Real-time Luas departures (e.g., HAR, STS, JER, TAL)
- `GET /api/v1/transit/search?query=phibsborough` - Search for stops by name
- `POST /api/v1/transit/commute` - Plan a custom commute with walk time

**User configuration:**  
Personalised stops are defined in `apps/api/app/data/user_stops.py`.  
Stop IDs are **placeholders** — verify actual IDs at https://www.transportforireland.ie/plan-a-journey/ and update the file.

Common Luas stop abbreviations: HAR (Harcourt), STS (St. Stephen's Green), JER (Jervis), TAL (Tallaght), BRI (Broombridge).

**Smoke test:**
```sh
# Personalised commute
curl http://localhost:8000/api/v1/transit/commute/to-work
curl http://localhost:8000/api/v1/transit/commute/to-home

# Generic stop lookup
curl http://localhost:8000/api/v1/transit/luas/stop/HAR
curl http://localhost:8000/api/v1/transit/bus/stop/334
```

### Vercel

- `GET /api/v1/vercel/projects` - List Vercel projects
- `GET /api/v1/vercel/deployments` - List deployments
- `POST /api/v1/vercel/stop` - Stop in-progress deployments
- `POST /api/v1/vercel/stop-production` - Stop production deployments

## Running Locally

From the workspace root:

```bash
# Install dependencies
cd apps/api
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

Or use turbo from the root:

```bash
turbo dev
```

## Transit Data Sources

- **Dublin Bus**: Requires TFI (Transport for Ireland) API key
  - Register at `https://developer.nationaltransport.ie/`
  - Subscribe to GTFS-R API (15 min activation time)
  - API endpoint: `https://api.nationaltransport.ie/gtfsr/v2/`
  - **Note**: Legacy SmartDublin RTPI endpoint (`data.smartdublin.ie`) has been deprecated
  
- **Luas**: Uses official RPA forecast API (keyless, XML)
  - `https://luasforecasts.rpa.ie/xml/get.ashx`
  - Stop abbreviations: JER (Jervis), STS (St. Stephen's Green), TAL (Tallaght), CON (Connolly), BRI (Broombridge), etc.
  - **Status**: ✅ Fully functional (tested 2026-04-19)

- **Rate Limits**: Service implements 30-second in-memory cache to minimize API calls

## Luas Stop Abbreviations (Common)

| Abbreviation | Stop Name |
|--------------|-----------|
| JER | Jervis (Red Line) |
| CON | Connolly (Red Line) |
| TAL | Tallaght (Red Line) |
| STS | St. Stephen's Green (Green Line) |
| BRI | Broombridge (Green Line) |
| RAN | Ranelagh (Green Line) |
| SAN | Sandyford (Green Line) |
