# Home Assistant Setup Guide

This guide explains how to connect AI-Life to your local Home Assistant instance for presence/location detection.

## Prerequisites

- Home Assistant installed and running on your local network
- Access to the Home Assistant web UI
- Home Assistant accessible at `http://homeassistant.local:8123` (or custom URL)

## Step 1: Generate a Long-Lived Access Token

1. Open your Home Assistant web UI
2. Click your **profile icon** in the bottom-left corner
3. Scroll down to the **"Long-Lived Access Tokens"** section
4. Click **"Create Token"**
5. Give it a descriptive name: `AI-Life Integration`
6. Copy the token immediately (it's only shown once)

## Step 2: Store the Token Securely

Create a token file in the `.secrets` directory:

```bash
# From the apps/api directory
mkdir -p .secrets
echo "YOUR_TOKEN_HERE" > .secrets/home_assistant_token.txt
```

**Important:** Do NOT commit this file to git. The `.secrets/` directory is already gitignored.

## Step 3: Configure the Home Assistant URL

Add to your `.env` file (or set as environment variable):

```bash
HOME_ASSISTANT_URL=http://homeassistant.local:8123
```

If your Home Assistant runs on a different URL or port:
```bash
HOME_ASSISTANT_URL=http://192.168.1.100:8123
```

## Step 4: Test the Connection

Run the service test script:

```bash
# Activate your virtual environment first
source .venv-1/bin/activate

# Test the Home Assistant connection
python -m app.services.home_assistant_service
```

You should see:
```
Connection status: {'status': 'ok', 'message': 'API running', ...}
Person: Declan
State: home
Location: (53.xxxx, -6.xxxx)
...
```

## Step 5: Configure Person Entities (if needed)

Home Assistant should automatically detect person entities from your mobile device trackers. 

To check your person entities:
1. Go to **Settings** → **People** in Home Assistant UI
2. Verify your person entity exists (e.g., `person.declan`)
3. Ensure at least one device tracker is linked to the person

Common device trackers:
- **Home Assistant Companion App** (iOS/Android) — best option
- **UniFi Network integration** — if you have UniFi access points
- **Router integration** — device_tracker from your router
- **OwnTracks** — self-hosted location tracking

## Troubleshooting

### Connection Refused / Timeout
- Check that Home Assistant is running: `ping homeassistant.local`
- Try the IP address instead of `.local` hostname
- Ensure port 8123 is accessible (check firewall)

### 401 Unauthorized
- Token may be invalid or expired
- Regenerate token in Home Assistant UI
- Ensure no extra whitespace in `.secrets/home_assistant_token.txt`

### 404 Entity Not Found
- Person entity doesn't exist or has different ID
- Check entity ID in HA UI: **Developer Tools** → **States** → search for `person.`
- Update your code to use the correct entity ID

### Person State Always "unknown"
- No device trackers linked to the person entity
- Install Home Assistant Companion App on your phone
- Link the device tracker to your person entity in Settings → People

## Security Notes

- **Token has full API access** — treat it like a password
- **Local network only by default** — Home Assistant not exposed to internet
- **Read-only for now** — AI-Life only reads entity states
- Future write operations (locks, alarms) will require approval-card gates

## What AI-Life Uses This For

- **Presence detection:** Know when you're home/away for context-aware automations
- **Location zones:** Detect "home", "work", custom zones for transit timing
- **Departure calculations:** "When should I leave for work?" based on current location
- **Context signals:** Combine presence + calendar + time for intelligent routines

## Next Steps

Once connected, the Home Assistant service provides:
- `get_person_state(person_id)` — current location zone
- `is_home(person_id)` — boolean home check
- `get_entity_state(entity_id)` — any HA entity state
- Future: Subscribe to state changes via WebSocket for real-time updates

The service is used by AI-Life's orchestration layer to make context-aware decisions without rule-based automation complexity.
