"""Test data for local development."""
from contextlib import closing

from app.db.connection import connect, database_path, init_db


def main() -> None:
    path = database_path()
    init_db(path)
    with closing(connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO major_roadmaps (major_code, title, degree_type, description) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(major_code) DO NOTHING",
            ("SAMPLE", "Sample development roadmap", "Sample", "Synthetic sample; no courses assigned."),
        )
    print(f"Sample roadmap ensured in {path}; existing records preserved.")


if __name__ == "__main__":
    main()
