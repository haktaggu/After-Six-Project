from __future__ import annotations

import argparse
from contextlib import contextmanager
import logging
from pathlib import Path
from urllib.parse import urlsplit

from app.features import ingest
from app.jobs.refresh_catalog import refresh_roadmap_catalog
from app.jobs.refresh_enrollment_policies import refresh_enrollment_policies
from app.schemas import RefreshResult


@contextmanager
def catalog_browser(headed: bool = False):
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError as error:
        raise ingest.SourceUnavailable('Playwright is unavailable. Rebuild the worker image.') from error

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not headed)
            page = browser.new_page()
            if headed:
                logging.info('Complete any verification in the Chromium window.')

            def fetch_html(url: str) -> str:
                ingest.check_source(url)
                parsed = urlsplit(url)
                if parsed.path.startswith('/preview_course'):
                    selector = '#course_preview_title, #course-title'
                elif parsed.path == '/preview_program.php':
                    selector = '.acalog-core h3'
                else:
                    selector = '#acalog-navigation'
                response = page.goto(url, wait_until='domcontentloaded', timeout=30_000)
                try:
                    page.locator(selector).first.wait_for(
                        state='attached', timeout=120_000 if headed else 15_000,
                    )
                except TimeoutError as error:
                    status = response.status if response else 'unknown'
                    raise ingest.SourceUnavailable(
                        f'Catalog page did not load (HTTP {status}): {url}. Cached data retained.',
                    ) from error
                ingest.check_source(page.url)
                return page.content()

            yield fetch_html
    except Error as error:
        raise ingest.SourceUnavailable(f'Chromium: {str(error).splitlines()[0]}') from error


def refresh_catalog_with_browser(path: Path) -> RefreshResult:
    with catalog_browser() as fetch_html:
        result = refresh_roadmap_catalog(path, fetch_html)
    try:
        refresh_enrollment_policies(path)
    except (ValueError, OSError, ingest.SourceUnavailable) as error:
        logging.getLogger(__name__).warning('Department enrollment paths could not be refreshed: %s', error)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Check an official course page without changing the database.')
    parser.add_argument('--probe', required=True, metavar='COURSE_URL')
    parser.add_argument('--headed', action='store_true', help='Show Chromium for manual verification.')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        with catalog_browser(args.headed) as fetch_html:
            course = ingest.parse_catalog(fetch_html(args.probe), args.probe).courses[0]
        print(course.model_dump_json(indent=2))
    except (ingest.SourceUnavailable, ValueError, OSError) as error:
        parser.exit(1, f'Catalog probe failed: {error}\n')


if __name__ == '__main__':
    main()
