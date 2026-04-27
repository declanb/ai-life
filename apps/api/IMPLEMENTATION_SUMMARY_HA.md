# Home Assistant Integration — Implementation Summary

**Delivered for:** Chief Architect  
**Feature:** Presence/location detection for "when to leave" orchestration  
**Status:** ✅ Ready for testing (pending user token setup)

---

## What Was Implemented

### 1. Core Service: `home_assistant_service.py`

Location: [apps/api/app/services/home_assistant_service.py](../services/home_assistant_service.py)

**Class:** `HomeAssistantService`

**Key Methods:**
- `get_entity_state(entity_id: str)` — Generic HA entity state reader
- `get_person_state(person_id: str)` — Presence/location for a person entity
- `is_home(person_id: str)` — Boolean home check
- `get_location_zone(person_id: str)` — Current zone name ("home", "work", etc.)
- `list_persons()` — All configured person entities
- `check_connection()` — Health check / test connection

**Authentication:**
- Long-lived access token from `.secrets/home_assistant_token.txt`
- URL from env var `HOME_ASSISTANT_URL` (defaults to `http://homeassistant.local:8123`)

**Error Handling:**
- Graceful fallback if HA unreachable (returns `None` instead of crashing)
- Logs warnings for missing config
- HTTP errors handled with retry-safe patterns

**Security:**
- Read-only operations only
- Token never logged or sent to LLM
- Local network only by default

---

## What Was Configured

### 2. Settings: `apps/api/app/core/settings.py`

Added fields:
```python
home_assistant_url: Optional[str] = None
home_assistant_token_file: Path = SECRETS_DIR / "home_assistant_token.txt"
```

Follows existing pattern from Google Calendar and Spotify OAuth services.

### 3. Environment Variables: `.env.example`

Added documentation:
```bash
HOME_ASSISTANT_URL=http://homeassistant.local:8123
```

With instructions on how to obtain the long-lived access token.

---

## Setup Guide

### User Actions Required

See [HOME_ASSISTANT_SETUP.md](../HOME_ASSISTANT_SETUP.md) for full guide.

**Quick setup:**
1. Generate long-lived access token in HA UI (Profile → Long-Lived Access Tokens)
2. Save token to `apps/api/.secrets/home_assistant_token.txt`
3. Set `HOME_ASSISTANT_URL=http://homeassistant.local:8123` in `.env`
4. Test: `python -m app.services.home_assistant_service`

---

## Usage Examples

### For Chief Architect: Integration into "When to Leave"

See [home_assistant_example.py](../services/home_assistant_example.py) for full code.

**Example 1: Get current location**
```python
from app.services.home_assistant_service import HomeAssistantService

service = HomeAssistantService()
zone = service.get_location_zone("declan")
print(f"User is at: {zone}")  # "home", "work", "not_home", etc.
```

**Example 2: Calculate departure time**
```python
# Check where user currently is
if service.is_home("declan"):
    # User is home, calculate transit from home → work
    transit_time = calculate_transit_time("home", "work")
else:
    # User is elsewhere, different calculation
    current_zone = service.get_location_zone("declan")
    transit_time = calculate_transit_time(current_zone, "work")

departure_time = arrival_time - transit_time - buffer
```

**Example 3: Presence-aware automation**
```python
person_state = service.get_person_state("declan")
if person_state:
    if person_state["state"] == "home":
        # User just arrived home
        last_changed = datetime.fromisoformat(person_state["last_changed"])
        if (datetime.now(timezone.utc) - last_changed) < timedelta(minutes=10):
            # Arrived within last 10 minutes → trigger "welcome home" routine
            pass
```

---

## What's NOT Implemented Yet (Future)

- **WebSocket subscriptions** for real-time state change notifications
- **Write operations** (triggering automations, setting states) — requires approval-card gates
- **Zone management** (reading custom zone definitions)
- **Device tracker selection** (choosing which tracker to trust if multiple sources)
- **Router integration** — API integration in FastAPI with proper error handling

Next step: Wire into a FastAPI router for REST API exposure if needed by `apps/web`.

---

## Dependencies

- `httpx` — Already in `requirements.txt` ✅
- `pydantic-settings` — Already in use ✅
- No new dependencies added

---

## Testing

**Manual test:**
```bash
cd apps/api
source .venv-1/bin/activate
python -m app.services.home_assistant_service
```

**Expected output:**
```
Connection status: {'status': 'ok', 'message': 'API running', ...}
Person: Declan
State: home
Location: (53.xxxx, -6.xxxx)
Source: device_tracker.iphone
✓ User is home
Configured persons: 1
  - Declan: home
```

---

## Integration Checklist for Chief Architect

- [ ] User has Home Assistant running locally
- [ ] User generates long-lived access token
- [ ] User stores token in `.secrets/home_assistant_token.txt`
- [ ] User sets `HOME_ASSISTANT_URL` in `.env`
- [ ] Test connection: `python -m app.services.home_assistant_service`
- [ ] Integrate into "when to leave" orchestration (use examples above)
- [ ] (Optional) Create FastAPI router at `apps/api/app/api/routers/home_assistant.py`
- [ ] (Optional) Create Next.js dashboard at `apps/web/components/home/HomeDashboard.tsx`

---

## Security & Privacy Notes

✅ **Local-first:** HA runs on local network, not cloud  
✅ **Token storage:** `.secrets/` directory (gitignored)  
✅ **Read-only:** No write operations yet  
✅ **No PII logging:** Entity states logged at warning level only, not in normal operation  
✅ **Future write gates:** All state changes will require approval-card confirmation

---

## Handoff Notes

**What works now:**
- Read person presence/location state
- Check if user is home
- Get any entity state (sensors, switches, etc.)
- Connection health checks

**What needs your decision:**
- Entity IDs: User must tell us their person entity name (default: `person.declan`)
- REST API exposure: Do you want a `/api/home-assistant/presence` endpoint?
- UI surface: Should presence show in a dashboard component?
- Approval-card design: How should write operations be gated?

**Recommended next step:**
Integrate `get_location_zone()` into your departure-time calculation flow, using the pattern in `home_assistant_example.py`. Once that works, we can discuss adding automation triggers (e.g., "turn on lights when I arrive home after sunset").

---

**Questions for user:**
1. What is your Home Assistant URL? (if not `homeassistant.local`)
2. What is your person entity ID? (check in HA UI: Developer Tools → States → `person.`)
3. Do you have any custom zones configured beyond "home" and "work"?

**Next implementation step (after testing):**
Create `apps/api/app/api/routers/home_assistant.py` with REST endpoints for the web UI to consume, following the pattern from `routers/vercel.py`.
