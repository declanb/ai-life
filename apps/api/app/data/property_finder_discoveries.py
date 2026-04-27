"""Discoveries log — tracks new listings seen each refresh cycle."""
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

_PATH = Path(__file__).parent / "property_finder_discoveries.json"
_LOCK = Lock()
_MAX_HISTORY = 200


def _read() -> dict:
    if not _PATH.exists():
        return {"seen_canonical_ids": [], "events": [], "last_run_at": None}
    try:
        with _PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Defensive: ensure required keys
        data.setdefault("seen_canonical_ids", [])
        data.setdefault("events", [])
        data.setdefault("last_run_at", None)
        return data
    except (json.JSONDecodeError, OSError):
        return {"seen_canonical_ids": [], "events": [], "last_run_at": None}


def _write(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with _PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_run(current_canonical_ids: list[str], source_summary: dict) -> dict:
    """
    Record a refresh run. Returns the diff: {new: [...], gone: [...], total_new: N}.
    """
    with _LOCK:
        state = _read()
        seen = set(state["seen_canonical_ids"])
        current = set(current_canonical_ids)

        new_ids = sorted(current - seen)
        gone_ids = sorted(seen - current)

        now = datetime.now(timezone.utc).isoformat()
        event = {
            "at": now,
            "new_ids": new_ids,
            "gone_ids": gone_ids,
            "total_listings": len(current),
            "sources": source_summary,
        }
        state["events"].append(event)
        state["events"] = state["events"][-_MAX_HISTORY:]
        state["seen_canonical_ids"] = sorted(current | seen)  # union — never forget
        state["last_run_at"] = now
        _write(state)

        return {
            "new": new_ids,
            "gone": gone_ids,
            "total_new": len(new_ids),
            "last_run_at": now,
        }


def get_state() -> dict:
    with _LOCK:
        return _read()


def get_recent_new_ids(limit: int = 20) -> list[str]:
    """Return canonical_ids that appeared in the last N events."""
    with _LOCK:
        state = _read()
        new_ids: list[str] = []
        for event in reversed(state.get("events", [])):
            new_ids.extend(event.get("new_ids", []))
            if len(new_ids) >= limit:
                break
        # Dedupe preserving order
        seen: set[str] = set()
        out: list[str] = []
        for nid in new_ids:
            if nid not in seen:
                seen.add(nid)
                out.append(nid)
        return out[:limit]
