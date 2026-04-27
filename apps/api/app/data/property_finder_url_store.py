"""Property Finder URL store — persists pasted listing URLs to disk."""
import json
from pathlib import Path
from threading import Lock

_STORE_PATH = Path(__file__).parent / "property_finder_urls.json"
_LOCK = Lock()


def _read() -> list[str]:
    if not _STORE_PATH.exists():
        return []
    try:
        with _STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(u) for u in data if isinstance(u, str)]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _write(urls: list[str]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)


def list_urls() -> list[str]:
    with _LOCK:
        return _read()


def add_urls(new_urls: list[str]) -> int:
    with _LOCK:
        urls = _read()
        for u in new_urls:
            u = u.strip()
            if u and u not in urls:
                urls.append(u)
        _write(urls)
        return len(urls)


def remove_url(url: str) -> bool:
    with _LOCK:
        urls = _read()
        if url in urls:
            urls.remove(url)
            _write(urls)
            return True
        return False
