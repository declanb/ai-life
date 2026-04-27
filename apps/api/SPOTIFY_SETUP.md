# Spotify Integration Setup

This guide walks through setting up Spotify integration for AI-Life's Physical Layer.

## Prerequisites

- Spotify Premium account (required for playback control API)
- Your account: `declan.butler@ie.ey.com`

## Step 1: Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click **Create app**
4. Fill in:
   - **App name:** `AI-Life Smart Home`
   - **App description:** `Personal smart home assistant with context-aware music`
   - **Redirect URI:** `http://127.0.0.1:8765`
   - **Which API/SDKs are you planning to use?** Check **Web API**
5. Agree to Terms of Service and click **Save**

## Step 2: Get Your Credentials

1. Click on your new app in the dashboard
2. Click **Settings** (top right)
3. Copy your **Client ID**
4. Keep this page open (you'll need it in a moment)

## Step 3: Create Client Config File

Create `apps/api/.secrets/spotify_oauth_client.json`:

```json
{
  "client_id": "YOUR_CLIENT_ID_FROM_STEP_2",
  "redirect_uri": "http://127.0.0.1:8765"
}
```

Replace `YOUR_CLIENT_ID_FROM_STEP_2` with the actual Client ID from the Spotify dashboard.

**Security:** This file is gitignored. Never commit it.

## Step 4: Run OAuth Flow

```bash
cd apps/api
python -m app.cli.spotify_auth
```

This will:
1. Start a local server on port 8765
2. Open your browser to Spotify's authorization page
3. Ask you to grant permissions
4. Exchange the authorization code for tokens
5. Save tokens to `apps/api/.secrets/spotify_oauth_token.json`
6. Test the API connection

## Step 5: Verify Setup

The auth script will show:
- ✅ Your Spotify display name and email
- ✅ Your account type (should be "premium")
- ✅ Any active Spotify devices (speakers, computers, phones)

## API Endpoints Available

Once authenticated, the following endpoints are available at `http://localhost:8000/api/v1/spotify`:

### Read
- `GET /playback` - Current playback state
- `GET /devices` - Available Spotify Connect devices
- `GET /playlists` - Your playlists
- `GET /user` - Your profile

### Control
- `POST /play` - Start/resume playback
- `POST /pause` - Pause playback
- `POST /next` - Skip to next track
- `POST /previous` - Skip to previous track
- `PUT /volume` - Set volume (0-100)
- `PUT /shuffle` - Toggle shuffle
- `PUT /repeat` - Set repeat mode

## Scopes Granted

The integration requests these permissions:

- `user-read-playback-state` - See what's playing
- `user-modify-playback-state` - Control playback
- `user-read-currently-playing` - Current track details
- `playlist-read-private` - Access your playlists
- `user-read-private` - Basic profile info
- `user-top-read` - Your top tracks/artists (for smart recommendations)
- `user-read-recently-played` - Recently played history

## Token Refresh

Access tokens expire after 1 hour. The service automatically refreshes them using your refresh token (which doesn't expire unless you revoke access in Spotify settings).

## Troubleshooting

### "Port 8765 already in use"
Kill any process using that port:
```bash
lsof -ti :8765 | xargs kill -9
```

### "No active devices found"
Start Spotify on any device (phone, computer, smart speaker). The device must be actively running Spotify to appear in the API.

### "Authorization failed"
1. Check your Client ID is correct
2. Ensure redirect URI exactly matches: `http://127.0.0.1:8765`
3. Verify the redirect URI is added to your app settings in Spotify Dashboard

## Next: Context-Aware Automations

With Spotify connected, you can now:

1. **Calendar-driven music:** Play focus playlist when "Deep Work" event starts
2. **Presence-based:** Pause when you leave home geofence
3. **Scene integration:** Lower volume when calendar call starts
4. **Adaptive playlists:** Morning energizing → afternoon focus → evening wind-down

These will be orchestrated through the `apps/api` service, exposed via approval cards in `apps/web`.

## Revoking Access

To revoke AI-Life's access:
1. Go to [Spotify Account Settings](https://www.spotify.com/account/apps/)
2. Find "AI-Life Smart Home"
3. Click **Remove Access**
4. Delete `apps/api/.secrets/spotify_oauth_token.json`
