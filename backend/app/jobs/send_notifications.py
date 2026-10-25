from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
from app.db.connection import connect, database_path, init_db
from app.errors import ApiProblem
from app.features import notifications
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning
from app.schemas import DeliveryTarget, SeatOpeningEvent

def send_notifications(path: Path) -> int:
    with closing(connect(path)) as db:
        rows = db.execute('SELECT id,section_id,previous_seats,new_seats,detected_at FROM availability_events WHERE processed_at IS NULL ORDER BY detected_at,id').fetchall()
        for row in rows:
            event = SeatOpeningEvent(**dict(zip(('id', 'section_id', 'previous_seats', 'new_seats', 'detected_at'), row)))
            notifications.dispatch_opening_event(db, event)
        rows = db.execute("SELECT id,event_id,student_id,section_id,message FROM notification_logs WHERE status='pending' ORDER BY created_at,id").fetchall()
        for row in rows:
            target = DeliveryTarget(**dict(zip(('delivery_id', 'event_id', 'student_id', 'section_id', 'message'), row)))
            try:
                notifications.deliver_notification(db, target)
            except Exception:
                with db:
                    db.execute("UPDATE notification_logs SET status='failed',sent_at=NULL,last_error='DELIVERY_ERROR' WHERE id=? AND status='pending'", (target.delivery_id,))
        return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description='Process opening events and pending Discord deliveries once.')
    parser.parse_args()
    try:
        path = database_path()
        init_db(path)
        with exclusive_worker(path):
            print(f'{send_notifications(path)} deliveries processed.')
    except ApiProblem as exc:
        parser.exit(1, f'Notification dispatch failed ({exc.code}).\n')
    except WorkerAlreadyRunning as exc:
        parser.exit(1, f'{exc}\n')
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Notification dispatch failed: {exc}\n')


if __name__ == "__main__":
    main()
