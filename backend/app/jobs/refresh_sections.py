from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
from app.db.connection import database_path, init_db
from app.errors import ApiProblem, ScaffoldPending
from app.features import ingest
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning
from app.jobs.send_notifications import send_notifications
from app.schemas import RefreshResult

# - Read SCHEDULE_SOURCE_URL (default https://www.sjsu.edu/classes/schedules/fall-2026.php).
#   Fetch and parse through ingest.fetch_source(url)/parse_schedule(html,term,url) before writing.
# - Open a fresh connection; BEGIN IMMEDIATE and call ingest.upsert_sections(db,document,checked_at).
#   checked_at is UTC ISO 8601. Commit related rows, seats, freshness and events together.
# - Return RefreshResult(updated_records,event_ids,checked_at). On failure roll back and keep
#   cached rows/freshness. Keep every imported term/section; do not hard-code a demo subset.
# - Source samples live under demo/sources/schedules/ with URL/capture time. Preserve unknown
#   seats and TBA meetings. The runner calls this on startup/every SCHEDULE_REFRESH_SECONDS
#   (default 300), using SCHEDULE_TERM. Return after commit so it can dispatch notifications.
# - No timer, seed logic or Discord request inside this function. Raise on fetch/parse/write
#   failures so the runner can retain cached data and retry the next scheduled refresh.
def refresh_sections(path: Path, term: str = "fall-2026") -> RefreshResult:
    raise ScaffoldPending("jobs.refresh_sections")


def main() -> None:
    parser = argparse.ArgumentParser(description='Import a term schedule once and dispatch new opening events.')
    parser.add_argument('--term', default='fall-2026')
    args = parser.parse_args()
    try:
        path = database_path()
        init_db(path)
        with exclusive_worker(path):
            result = refresh_sections(path, args.term)
            print(f'Imported {result.updated_records} section records at {result.checked_at}.')
            if result.event_ids:
                print(f'{send_notifications(path)} deliveries processed.')
    except NotImplementedError:
        parser.exit(1, 'Schedule import or notification dispatch needs its assigned implementation.\n')
    except ApiProblem as exc:
        parser.exit(1, f'Schedule command failed ({exc.code}).\n')
    except WorkerAlreadyRunning as exc:
        parser.exit(1, f'{exc}\n')
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Schedule command failed: {exc}\n')


if __name__ == "__main__":
    main()
