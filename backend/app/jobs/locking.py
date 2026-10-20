from contextlib import contextmanager
import fcntl
from pathlib import Path
from typing import Iterator


class WorkerAlreadyRunning(RuntimeError):
    pass


@contextmanager
def exclusive_worker(path: Path) -> Iterator[None]:
    lock_path = path.with_name(path.name + '-worker.lock')
    with lock_path.open('a') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise WorkerAlreadyRunning('The automatic worker is running. Stop it before running a job manually.') from None
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
