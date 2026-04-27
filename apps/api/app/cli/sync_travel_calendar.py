"""CLI wrapper for syncing the AI-Life travel calendar.

Run periodically (e.g. via launchd/cron):
    cd apps/api && python -m app.cli.sync_travel_calendar

Reads the next 7 days from the user's primary Google Calendar, computes
leave-at times for work events, and syncs them to the dedicated travel calendar.
"""
from __future__ import annotations

import sys

from app.services.google_calendar_service import GoogleCalendarService


def main() -> int:
    try:
        service = GoogleCalendarService()
        print("🔄 Syncing travel calendar...")
        stats = service.sync_travel_events(dry_run=False)

        print(f"✅ Sync complete:")
        print(f"   Created: {stats['created']}")
        print(f"   Updated: {stats['updated']}")
        print(f"   Deleted: {stats['deleted']} (orphaned)")
        print(f"   Skipped: {stats['skipped']} (no work location or all-day)")

        if stats["errors"]:
            print(f"\n⚠️  {len(stats['errors'])} error(s):")
            for err in stats["errors"]:
                print(f"   - {err}")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
