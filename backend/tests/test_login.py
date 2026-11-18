from contextlib import closing

from fastapi.testclient import TestClient

from app.api.common import SESSION_COOKIE
from app.db.connection import connect
from app.features.auth import register_user
from app.main import create_app
from app.schemas import SignupRequest


CREDENTIALS = {"email": "student@example.com", "password": "example-password"}

def test_login_replaces_stale_session_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-that-is-at-least-32-bytes")

    with TestClient(create_app(tmp_path / "test.db")) as client:
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        response = client.post("/api/auth/signup", json={**CREDENTIALS, "full_name": "Test Student"},
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 201
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": response.json()["csrf_token"]}).status_code == 204
        client.cookies.set(SESSION_COOKIE, "stale-session", domain="testserver.local")
        assert client.get("/api/auth/session").status_code == 401

        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 403

        response = client.post(
            "/api/auth/login",
            json=CREDENTIALS,
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200
        assert client.get("/api/auth/session").status_code == 200


def test_generated_signing_key_keeps_sessions_valid_after_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    path = tmp_path / "test.db"

    with TestClient(create_app(path)) as client:
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/auth/signup",
            json={**CREDENTIALS, "full_name": "Test Student"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201
        session = client.cookies.get(SESSION_COOKIE)
        session_csrf = response.json()["csrf_token"]

    with TestClient(create_app(path)) as client:
        client.cookies.set(SESSION_COOKIE, session, domain="testserver.local")
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": session_csrf}).status_code == 204


def test_new_app_has_no_accounts_and_disabled_credentials_are_rejected(tmp_path):
    path = tmp_path / "test.db"
    with TestClient(create_app(path)) as client:
        with closing(connect(path)) as db:
            assert db.execute("SELECT count(*) FROM users").fetchone() == (0,)
            user = register_user(db, SignupRequest(**CREDENTIALS, full_name="Test Student"))
            with db:
                db.execute("UPDATE users SET password_hash='disabled' WHERE id=?", (user.id,))
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/auth/login", json=CREDENTIALS,
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 401
