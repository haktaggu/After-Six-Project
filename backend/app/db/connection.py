"""SQLite initialization and connection helpers. No sample data is loaded here."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3


def database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "data/oursjsu.db")))


def connect(path: Path) -> sqlite3.Connection:
    # Require an existing database; health checks must not create missing files.
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(__file__).with_name("schema.sql").read_text())


def check_connection(path: Path) -> None:
    with closing(connect(path)) as conn:
        conn.execute("SELECT count(*) FROM sqlite_schema").fetchone()
