from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
from app.db.connection import connect, database_path, init_db
from app.errors import ApiProblem
from app.features import notifications
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning

def send_notifications(path: Path) -> int:
    with closing(connect(path)) as db:
        return notifications.process_notifications(db)


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
