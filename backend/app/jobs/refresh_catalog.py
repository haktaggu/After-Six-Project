from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from app.db.connection import connect, database_path, init_db
from app.features import ingest
from app.jobs.locking import exclusive_worker
from app.jobs.refresh_roadmap import ROADMAP_INDEX, Roadmap, fetch_roadmap, save_roadmap
from app.schemas import IngestionDocument, RefreshResult

log = logging.getLogger(__name__)
CATALOG_HOME = 'https://catalog.sjsu.edu/'


def refresh_roadmap_catalog(path: Path, fetch_html: Callable[[str], str]) -> RefreshResult:
    roadmap = fetch_roadmap(os.environ.get('ROADMAP_SOURCE_URL') or ROADMAP_INDEX, fetch_html)
    courses = []
    for entry in roadmap.courses:
        try:
            course = ingest.parse_catalog(fetch_html(entry.url), entry.url).courses[0]
            if course.course.id != entry.course_id:
                raise ValueError(f'Catalog detail did not match {entry.course_id}')
        except (ValueError, OSError, ingest.SourceUnavailable) as error:
            raise ingest.SourceUnavailable(f'{entry.course_id}: {error}; cached roadmap and catalog retained') from error
        courses.append(course)
        log.info('Fetched %s (%s/%s)', entry.course_id, len(courses), len(roadmap.courses))

    document = IngestionDocument(terms=[], courses=courses, sections=[])
    return save_catalog(path, document, roadmap)


def refresh_catalog(path: Path) -> RefreshResult:
    url = os.environ.get('CATALOG_SOURCE_URL') or CATALOG_HOME
    if urlsplit(url).path in ('/preview_course.php', '/preview_course_nopop.php'):
        return save_catalog(path, ingest.parse_catalog(ingest.fetch_source(url), url))
    return refresh_roadmap_catalog(path, ingest.fetch_source)


def save_catalog(path: Path, document: IngestionDocument, roadmap: Roadmap | None = None) -> RefreshResult:
    if not document.courses:
        raise ValueError('Catalog import produced no courses; cached catalog retained')
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        count = ingest.upsert_catalog(db, document)
        if roadmap is not None:
            save_roadmap(db, roadmap)
    return RefreshResult(updated_records=count, event_ids=[], checked_at=datetime.now(timezone.utc).isoformat())


def main() -> None:
    parser = argparse.ArgumentParser(description='Import the configured catalog once.')
    parser.parse_args()
    path = database_path()
    init_db(path)
    with exclusive_worker(path):
        result = refresh_catalog(path)
    print(f'Imported {result.updated_records} catalog records.')


if __name__ == '__main__':
    main()
