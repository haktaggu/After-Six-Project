from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
from app.db.connection import connect, database_path, init_db
from app.errors import ApiProblem, ScaffoldPending
from app.features import notifications
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning
from app.schemas import DeliveryTarget, SeatOpeningEvent

# - Open/close a fresh connection for this invocation. The single automatic worker calls this
#   after schedule imports and every NOTIFICATION_POLL_SECONDS (default 30). No timer here.
# - Read unprocessed availability_events in detected_at/id order; construct SeatOpeningEvent
#   {id,section_id,previous_seats:0,new_seats:positive int,detected_at:UTC} for each.
# - Call notifications.dispatch_opening_event(db,event); it owns its insert/processed transaction.
# - Read pending notification_logs in created_at/id order. Build DeliveryTarget with delivery_id
#   (the log ID),event_id,student_id,section_id,message; call deliver_notification(db,target).
# - Return the number of pending deliveries processed, including rejected ones. Never send sent
#   or failed rows again. Catch individual delivery failures, record a safe failure code and continue.
# - Do not hold a write transaction around network calls. Each helper commits its own changes.
#   Logs are unique per event/student; an unchanged scrape has no new opening event.
def send_notifications(path: Path) -> int:
    raise ScaffoldPending("jobs.send_notifications")


def main() -> None:
    parser = argparse.ArgumentParser(description='Process opening events and pending Discord deliveries once.')
    parser.parse_args()
    try:
        path = database_path()
        init_db(path)
        with exclusive_worker(path):
            print(f'{send_notifications(path)} deliveries processed.')
    except NotImplementedError:
        parser.exit(1, 'Notification dispatch needs its assigned feature implementation.\n')
    except ApiProblem as exc:
        parser.exit(1, f'Notification dispatch failed ({exc.code}).\n')
    except WorkerAlreadyRunning as exc:
        parser.exit(1, f'{exc}\n')
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Notification dispatch failed: {exc}\n')


if __name__ == "__main__":
    main()
