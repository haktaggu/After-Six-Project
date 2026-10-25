from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path

from app.db.connection import connect, database_path, init_db
from app.features import ingest
from app.jobs.locking import exclusive_worker
from app.jobs.refresh_catalog import SOURCES
from app.schemas import IngestionDocument, RefreshResult

log = logging.getLogger(__name__)


def import_snapshot(path: Path, name: str) -> RefreshResult:
    if name not in ('closed', 'open'):
        raise ValueError('Choose the closed or open replay snapshot')
    payload = json.loads((SOURCES / 'schedules' / f'{name}.json').read_text())
    document = IngestionDocument.model_validate(payload['document'])
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        return ingest.upsert_sections(db, document, payload['captured_at'])


def refresh_sections(path: Path, term: str = 'fall-2026') -> RefreshResult:
    if os.environ.get('DATA_MODE', 'live') == 'replay':
        with closing(connect(path)) as db:
            exists = db.execute('SELECT 1 FROM sections LIMIT 1').fetchone()
        if not exists:
            return import_snapshot(path, 'closed')
        return RefreshResult(updated_records=0, event_ids=[], checked_at=datetime.now(timezone.utc).isoformat())
    url = os.environ.get('SCHEDULE_SOURCE_URL', 'https://www.sjsu.edu/classes/schedules/fall-2026.php')
    document = ingest.parse_schedule(ingest.fetch_source(url), term, url)
    configured = os.environ.get('REVIEW_COURSE_IDS', '').strip()
    if configured:
        if configured == 'catalog':
            with closing(connect(path)) as db:
                allowed = {r[0] for r in db.execute('SELECT id FROM courses')}
        else:
            allowed = set(configured.split(','))
        sections = [s for s in document.sections if s.course.id in allowed]
        log.info('Explicit review subset: included %s sections; excluded %s.', len(sections), len(document.sections) - len(sections))
        document = document.model_copy(update={'sections': sections})
        if not sections:
            raise ValueError('Review subset matched no scheduled sections')
    now = datetime.now(timezone.utc).isoformat()
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        return ingest.upsert_sections(db, document, now)


def main() -> None:
    parser = argparse.ArgumentParser(description='Import the configured schedule once.')
    parser.add_argument('--term', default=os.environ.get('SCHEDULE_TERM', 'fall-2026'))
    args = parser.parse_args()
    path = database_path()
    init_db(path)
    with exclusive_worker(path):
        result = refresh_sections(path, args.term)
    print(f'Imported {result.updated_records} sections; {len(result.event_ids)} opening events.')


if __name__ == '__main__':
    main()
