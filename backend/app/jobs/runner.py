from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import signal
from threading import Event
import time
from typing import Callable

from app.db.connection import database_path, init_db
from app.errors import ApiProblem
from app.jobs.locking import exclusive_worker, WorkerAlreadyRunning
from app.jobs.refresh_catalog import refresh_catalog
from app.jobs.refresh_sections import refresh_sections
from app.jobs.send_notifications import send_notifications
from scripts.seed import seed_demo_account, seed_demo_courses

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    catalog_seconds: int = 86400
    schedule_seconds: int = 300
    notification_seconds: int = 30
    term: str = 'fall-2026'

    @classmethod
    def from_env(cls) -> Settings:
        intervals = {}
        for field, name, default in (
            ('catalog_seconds', 'CATALOG_REFRESH_SECONDS', 86400),
            ('schedule_seconds', 'SCHEDULE_REFRESH_SECONDS', 300),
            ('notification_seconds', 'NOTIFICATION_POLL_SECONDS', 30),
        ):
            raw = os.environ.get(name, str(default))
            try:
                value = int(raw)
            except ValueError:
                raise ValueError(f'{name} must be a positive integer.') from None
            if value < 1:
                raise ValueError(f'{name} must be a positive integer.')
            intervals[field] = value
        term = os.environ.get('SCHEDULE_TERM', 'fall-2026').strip()
        if not term:
            raise ValueError('SCHEDULE_TERM must not be empty.')
        return cls(**intervals, term=term)


class JobRunner:
    def __init__(self, path: Path, settings: Settings, clock: Callable[[], float] = time.monotonic):
        self.path = path
        self.settings = settings
        self.clock = clock
        self.due = {'catalog': 0.0, 'demo setup': 0.0, 'sections': 0.0, 'notifications': 0.0}
        self.problems: dict[str, str] = {}

    def run_job(self, name: str, action: Callable[[], object]) -> bool:
        try:
            action()
        except Exception as exc:
            if isinstance(exc, ApiProblem):
                problem = exc.code
            else:
                problem = type(exc).__name__
            if self.problems.get(name) != problem:
                log.warning('%s: %s; will try again later.', name, problem)
                self.problems[name] = problem
            return False
        self.problems.pop(name, None)
        if name != 'demo setup':
            log.info('%s completed.', name)
        return True

    def seed_courses(self) -> None:
        result = seed_demo_courses(self.path)
        if result.missing_course_ids:
            missing = ', '.join(result.missing_course_ids)
            if self.problems.get('demo courses') != missing:
                log.warning('Computer Engineering demo is waiting for imported courses: %s.', missing)
                self.problems['demo courses'] = missing
        else:
            if 'demo courses' in self.problems or result.history_created:
                log.info('Computer Engineering roadmap and initial history are ready.')
            self.problems.pop('demo courses', None)

    def tick(self, stop: Event) -> None:
        if not stop.is_set() and self.clock() >= self.due['catalog']:
            ok = self.run_job('catalog', lambda: refresh_catalog(self.path))
            delay = self.settings.catalog_seconds if ok else min(300, self.settings.catalog_seconds)
            self.due['catalog'] = self.clock() + delay
            if ok:
                self.due['demo setup'] = 0.0
        if not stop.is_set() and self.clock() >= self.due['demo setup']:
            self.run_job('demo setup', self.seed_courses)
            self.due['demo setup'] = self.clock() + min(300, self.settings.schedule_seconds)
        if not stop.is_set() and self.clock() >= self.due['sections']:
            ok = self.run_job('sections', lambda: refresh_sections(self.path, self.settings.term))
            self.due['sections'] = self.clock() + self.settings.schedule_seconds
            if ok:
                self.due['notifications'] = 0.0
        if not stop.is_set() and self.clock() >= self.due['notifications']:
            self.run_job('notifications', lambda: send_notifications(self.path))
            self.due['notifications'] = self.clock() + self.settings.notification_seconds

    def run(self, stop: Event) -> None:
        while not stop.is_set():
            self.tick(stop)
            delay = max(0.0, min(self.due.values()) - self.clock())
            stop.wait(min(delay, 1.0))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        settings = Settings.from_env()
        path = database_path()
        init_db(path)
        with exclusive_worker(path):
            seed_demo_account(path)
            log.info('Automatic jobs started: catalog=%ss, sections=%ss, notifications=%ss, term=%s.',
                     settings.catalog_seconds, settings.schedule_seconds, settings.notification_seconds, settings.term)
            JobRunner(path, settings).run(stop)
    except (ValueError, WorkerAlreadyRunning) as exc:
        log.error('%s', exc)
        raise SystemExit(1) from None
    log.info('Automatic jobs stopped.')


if __name__ == '__main__':
    main()
