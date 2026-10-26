from __future__ import annotations

import argparse
from contextlib import closing
import os

from app.db.connection import connect, database_path
from app.features.notifications import dispatch_opening_event
from app.jobs.locking import exclusive_worker
from app.jobs.refresh_sections import import_snapshot
from app.schemas import SeatOpeningEvent


def main() -> None:
    parser = argparse.ArgumentParser(description='Replay a schedule observation without sending external messages.')
    parser.add_argument('snapshot', choices=['closed', 'open'])
    args = parser.parse_args()
    if os.environ.get('DATA_MODE') != 'replay':
        parser.error('Use the replay Compose configuration and stop its worker first.')
    path = database_path()
    with exclusive_worker(path):
        result = import_snapshot(path, args.snapshot)
        with closing(connect(path)) as db:
            rows = db.execute('SELECT id,section_id,previous_seats,new_seats,detected_at FROM availability_events WHERE processed_at IS NULL ORDER BY detected_at,id').fetchall()
            count = 0
            for row in rows:
                count += dispatch_opening_event(db, SeatOpeningEvent(**dict(zip(('id','section_id','previous_seats','new_seats','detected_at'), row))))
    print(f'{result.updated_records} sections imported; {len(result.event_ids)} new openings; {count} pending deliveries. No external messages sent.')


if __name__ == '__main__':
    main()
