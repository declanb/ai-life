"""Spotify playback & control endpoints for AI-Life Physical Layer."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.spotify_service import SpotifyService


router = APIRouter(prefix="/spotify", tags=["spotify"])


def get_spotify_service() -> SpotifyService:
    return SpotifyService()


# --- Request Models -------------------------------------------------------


class PlayRequest(BaseModel):
    device_id: Optional[str] = Field(None, description="Target device ID (uses active device if omitted)")
    context_uri: Optional[str] = Field(None, description="Playlist/album/artist URI (e.g. spotify:playlist:...)")
    uris: Optional[list[str]] = Field(None, description="List of track URIs to play")


class VolumeRequest(BaseModel):
    volume_percent: int = Field(..., ge=0, le=100, description="Volume level (0-100)")
    device_id: Optional[str] = Field(None, description="Target device ID")


class ShuffleRequest(BaseModel):
    state: bool = Field(..., description="Enable or disable shuffle")
    device_id: Optional[str] = Field(None, description="Target device ID")


class RepeatRequest(BaseModel):
    state: str = Field(..., description="Repeat mode: 'track', 'context', or 'off'")
    device_id: Optional[str] = Field(None, description="Target device ID")


class DeviceRequest(BaseModel):
    device_id: Optional[str] = Field(None, description="Target device ID")


# --- Read Endpoints -------------------------------------------------------


@router.get("/playback")
async def get_playback(service: SpotifyService = Depends(get_spotify_service)):
    """Get current playback state (what's playing, device, shuffle, repeat, etc.)."""
    try:
        playback = service.get_current_playback()
        if playback is None:
            return {"is_playing": False, "message": "No active playback"}
        return playback
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/devices")
async def get_devices(service: SpotifyService = Depends(get_spotify_service)):
    """List available Spotify Connect devices."""
    try:
        return service.get_available_devices()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/playlists")
async def get_playlists(
    limit: int = 20,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Get user's playlists."""
    try:
        return service.get_user_playlists(limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/user")
async def get_user(service: SpotifyService = Depends(get_spotify_service)):
    """Get current user profile."""
    try:
        return service.get_current_user()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --- Control Endpoints ----------------------------------------------------


@router.post("/play")
async def play(
    request: PlayRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Start or resume playback. Can optionally specify context (playlist/album) or track URIs."""
    try:
        service.play(
            device_id=request.device_id,
            context_uri=request.context_uri,
            uris=request.uris,
        )
        return {"message": "Playback started"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/pause")
async def pause(
    request: DeviceRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Pause playback."""
    try:
        service.pause(device_id=request.device_id)
        return {"message": "Playback paused"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/next")
async def skip_next(
    request: DeviceRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Skip to next track."""
    try:
        service.skip_to_next(device_id=request.device_id)
        return {"message": "Skipped to next track"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/previous")
async def skip_previous(
    request: DeviceRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Skip to previous track."""
    try:
        service.skip_to_previous(device_id=request.device_id)
        return {"message": "Skipped to previous track"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/volume")
async def set_volume(
    request: VolumeRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Set playback volume (0-100)."""
    try:
        service.set_volume(
            volume_percent=request.volume_percent,
            device_id=request.device_id,
        )
        return {"message": f"Volume set to {request.volume_percent}%"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/shuffle")
async def set_shuffle(
    request: ShuffleRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Enable or disable shuffle."""
    try:
        service.set_shuffle(
            state=request.state,
            device_id=request.device_id,
        )
        return {"message": f"Shuffle {'enabled' if request.state else 'disabled'}"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/repeat")
async def set_repeat(
    request: RepeatRequest,
    service: SpotifyService = Depends(get_spotify_service),
):
    """Set repeat mode: 'track', 'context', or 'off'."""
    try:
        service.set_repeat(
            state=request.state,
            device_id=request.device_id,
        )
        return {"message": f"Repeat mode set to '{request.state}'"}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
