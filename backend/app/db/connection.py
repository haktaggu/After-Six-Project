from contextlib import closing
import os
import secrets
from pathlib import Path
import sqlite3


def database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "data/oursjsu.db")))


def connect(path: Path) -> sqlite3.Connection:
    # FastAPI can resume a request dependency on another worker thread.
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(__file__).with_name("schema.sql").read_text())
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(student_profiles)")}
            if "recommendation_limit" not in columns:
                conn.execute(
                    "ALTER TABLE student_profiles ADD COLUMN recommendation_limit INTEGER NOT NULL DEFAULT 4 "
                    "CHECK (typeof(recommendation_limit) = 'integer' AND recommendation_limit BETWEEN 1 AND 5)"
                )
            conn.execute(
                "INSERT OR IGNORE INTO session_signing_key (id, secret) VALUES (1, ?)",
                (secrets.token_bytes(32),),
            )


def check_connection(path: Path) -> None:
    with closing(connect(path)) as conn:
        conn.execute("SELECT count(*) FROM sqlite_schema").fetchone()
