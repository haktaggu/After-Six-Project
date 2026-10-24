from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
from app.db.connection import database_path, init_db
from app.errors import ApiProblem, ScaffoldPending
from app.features import ingest
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning
from app.schemas import RefreshResult

# - Read CATALOG_SOURCE_URL (default https://catalog.sjsu.edu/), then call ingest.fetch_source(url)
#   and ingest.parse_catalog(html,url) outside the write transaction.
# - Open/close a database connection for this invocation. In one transaction call
#   ingest.upsert_catalog(db,document) and commit; roll back on any failed write.
# - Return RefreshResult(updated_records=count,event_ids=[],checked_at=UTC ISO 8601).
#   Preserve cached data on fetch/parse failure. No deletion of omitted catalog records.
# - runner.py calls this on startup and daily. Return after committing; do not start a timer,
#   seed accounts, dispatch notifications or catch failures as a successful empty import.
# - IngestionDocument has terms[],courses:ImportedCourse[],sections[]; ImportedCourse has
#   course:Course and prerequisite_rule:RequirementRule. Keep verified source samples under
#   demo/sources/catalog/ with their URL and capture time; do not guess HTML selectors.
def refresh_catalog(path: Path) -> RefreshResult:
    raise ScaffoldPending("jobs.refresh_catalog")


def main() -> None:
    parser = argparse.ArgumentParser(description='Fetch and import the official course catalog once.')
    parser.parse_args()
    try:
        path = database_path()
        init_db(path)
        with exclusive_worker(path):
            result = refresh_catalog(path)
        print(f'Imported {result.updated_records} catalog records at {result.checked_at}.')
    except NotImplementedError:
        parser.exit(1, 'Catalog import needs its assigned feature implementation.\n')
    except ApiProblem as exc:
        parser.exit(1, f'Catalog import failed ({exc.code}).\n')
    except WorkerAlreadyRunning as exc:
        parser.exit(1, f'{exc}\n')
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Catalog import failed: {exc}\n')


if __name__ == "__main__":
    main()
