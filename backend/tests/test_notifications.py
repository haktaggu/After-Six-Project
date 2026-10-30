from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect
from app.main import create_app
from scripts.seed import DEMO_EMAIL, DEMO_PASSWORD, DEMO_STUDENT_ID

def insert_notification(
    path: Path,
    notification_id: str,
    student_id: str,
) -> None:
    with closing(connect(path)) as db, db:
        db.execute(
            "INSERT OR IGNORE INTO terms (id,name) VALUES (?,?)",
            ("fall-2026", "Fall 2026"),
        )

        db.execute(
            """
            INSERT OR IGNORE INTO courses
                (id,subject,catalog_number,title)
            VALUES (?,?,?,?)
            """,
            ("CMPE-131", "CMPE", "131", "Software Engineering I"),
        )

        db.execute(
            """
            INSERT OR IGNORE INTO sections
                (id,term,class_number,section_number,course_id,title,mode,source_url)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                "section-1",
                "fall-2026",
                "12345",
                "01",
                "CMPE-131",
                "Software Engineering I",
                "In Person",
                "https://example.test/section-1",
            ),
        )

        db.execute(
            """
            INSERT OR IGNORE INTO availability_events
                (id,section_id,previous_seats,new_seats,detected_at)
            VALUES (?,?,?,?,?)
            """,
            (
                "event-1",
                "section-1",
                0,
                1,
                "2026-10-29T12:00:00+00:00",
            ),
        )

        db.execute(
            """
            INSERT INTO notification_logs
                (id,event_id,student_id,section_id,event_type,message,status,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                notification_id,
                "event-1",
                student_id,
                "section-1",
                "section_opened",
                "A seat opened in CMPE 131.",
                "sent",
                "2026-10-29T12:00:00+00:00",
            ),
        )

@pytest.fixture
def notification_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        "SESSION_SECRET",
        "test-session-secret-that-is-at-least-32-bytes",
    )
    monkeypatch.setenv("DATA_MODE", "live")
    monkeypatch.setenv("CATALOG_INPUT", "live")

    database_path = tmp_path / "test.db"
    app = create_app(database_path)

    with TestClient(app) as client:
        csrf_response = client.get("/api/auth/csrf")
        assert csrf_response.status_code == 200
        login_csrf = csrf_response.json()["csrf_token"]

        login_response = client.post(
            "/api/auth/login",
            headers={"X-CSRF-Token": login_csrf},
            json={
                "email": DEMO_EMAIL,
                "password": DEMO_PASSWORD,
            },
        )
        assert login_response.status_code == 200
        session_csrf = login_response.json()["csrf_token"]

        insert_notification(
            database_path,
            "notification-1",
            DEMO_STUDENT_ID,
        )

        yield client, database_path, session_csrf

def test_notification_history_includes_unread_status(
    notification_client,
) -> None:
    client, _database_path, _csrf = notification_client

    response = client.get("/api/me/notifications")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "notification-1"
    assert response.json()["items"][0]["is_read"] is False

def test_mark_notification_read_updates_database(
    notification_client,
) -> None:
    client, database_path, csrf = notification_client

    response = client.patch(
        "/api/me/notifications/notification-1/read",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 204

    with closing(connect(database_path)) as db:
        row = db.execute(
            "SELECT is_read FROM notification_logs WHERE id=?",
            ("notification-1",),
        ).fetchone()

    assert row == (1,)

def test_mark_missing_notification_returns_404(
    notification_client,
) -> None:
    client, _database_path, csrf = notification_client

    response = client.patch(
        "/api/me/notifications/not-a-real-id/read",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

def test_student_cannot_mark_another_students_notification(
    notification_client,
) -> None:
    client, database_path, csrf = notification_client

    with closing(connect(database_path)) as db, db:
        db.execute(
            """
            INSERT INTO users
                (id,username,email,full_name,password_hash,created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (
                "other-user",
                "other",
                "other@example.test",
                "Other Student",
                "unused-test-hash",
                "2026-10-29T12:00:00+00:00",
            ),
        )

        db.execute(
            """
            INSERT INTO student_profiles (student_id,user_id)
            VALUES (?,?)
            """,
            ("other-student", "other-user"),
        )

    insert_notification(
        database_path,
        "other-notification",
        "other-student",
    )

    response = client.patch(
        "/api/me/notifications/other-notification/read",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 404

    with closing(connect(database_path)) as db:
        row = db.execute(
            "SELECT is_read FROM notification_logs WHERE id=?",
            ("other-notification",),
        ).fetchone()

    assert row == (0,)

def test_mark_notification_read_requires_csrf(
    notification_client,
) -> None:
    client, _database_path, _csrf = notification_client

    response = client.patch(
        "/api/me/notifications/notification-1/read"
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"