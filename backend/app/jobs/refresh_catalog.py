from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.db.connection import connect, database_path, init_db
from app.features import ingest
from app.jobs.locking import exclusive_worker
from app.schemas import IngestionDocument, RefreshResult

SOURCES = Path(__file__).resolve().parents[2] / 'demo' / 'sources'


def refresh_catalog(path: Path) -> RefreshResult:
    courses = {}
    if os.environ.get('CATALOG_INPUT', 'live') == 'snapshot' or os.environ.get('DATA_MODE', 'live') == 'replay':
        folder = Path(os.environ.get('CATALOG_SNAPSHOT_DIR', str(SOURCES / 'catalog')))
        entries = json.loads((folder / 'manifest.json').read_text())
        for entry in entries:
            doc = ingest.parse_catalog((folder / entry['file']).read_text(), entry['url'])
            courses.update({c.course.id: c for c in doc.courses})
    else:
        url = os.environ.get('CATALOG_SOURCE_URL', 'https://catalog.sjsu.edu/')
        queue = [url]
        visited = set()
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            html = ingest.fetch_source(url)
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.select_one('#course_preview_title')
            if title:
                doc = ingest.parse_catalog(html, url)
                courses.update({c.course.id: c for c in doc.courses})
                continue
            for link in soup.select('a[href]'):
                href = urljoin(url, link['href'])
                text = link.get_text(' ', strip=True).lower()
                if 'preview_course' in href or 'course descriptions' in text or 'filter[cpage]' in href or 'filter%5Bcpage%5D' in href:
                    ingest.check_source(href)
                    if href not in visited and href not in queue:
                        queue.append(href)
    if not courses:
        raise ValueError('Catalog import produced no courses; cached catalog retained')
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        count = ingest.upsert_catalog(db, IngestionDocument(terms=[], courses=list(courses.values()), sections=[]))
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
