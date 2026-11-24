from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
import secrets
from uuid import uuid4

from app.errors import ApiProblem
from app.schemas import AuthenticatedStudent, Database, LoginRequest, SessionGrant, SessionIdentity, SessionResponse, SignupRequest, User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f'scrypt$16384$8$1${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split('$') if isinstance(stored_hash, str) else []
    if len(parts) != 6 or parts[:4] != ['scrypt', '16384', '8', '1']:
        return False
    if len(parts[4]) != 32 or len(parts[5]) != 64:
        return False
    try:
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(parts[4]), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, bytes.fromhex(parts[5]))
    except (ValueError, UnicodeError):
        return False


DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


def register_user(db: Database, body: SignupRequest) -> User:
    name = body.full_name.strip()
    email = body.email.strip().lower()
    if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Enter a name and a valid email address')
    user = User(id=str(uuid4()), email=email, full_name=name, created_at=datetime.now(timezone.utc).isoformat())
    password_hash = hash_password(body.password)
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM users WHERE lower(email)=?', (email,)).fetchone():
            raise ApiProblem(409, 'ACCOUNT_EXISTS', 'An account already exists for that email')
        db.execute(
            'INSERT INTO users (id,username,email,full_name,password_hash,created_at) VALUES (?,?,?,?,?,?)',
            (user.id, user.id, email, name, password_hash, user.created_at),
        )
        db.execute('INSERT INTO student_profiles (student_id,user_id,recommendation_limit) VALUES (?,?,?)',
                   (user.id, user.id, 4))
    return user


def session_secret(db: Database) -> bytes:
    configured = os.environ.get('SESSION_SECRET')
    if configured:
        secret = configured.encode()
        if len(secret) < 32:
            raise ValueError('SESSION_SECRET must contain at least 32 bytes.')
        return secret
    return db.execute('SELECT secret FROM session_signing_key WHERE id=1').fetchone()[0]


def authenticate_user(db: Database, body: LoginRequest) -> User:
    row = db.execute('SELECT id,email,full_name,created_at,password_hash FROM users WHERE lower(email)=?',
                     (body.email.strip().lower(),)).fetchone()
    valid = verify_password(body.password, row[4] if row else DUMMY_HASH)
    if not row or not valid:
        raise ApiProblem(401, 'INVALID_CREDENTIALS', 'Email or password is incorrect')
    return User(id=row[0], email=row[1], full_name=row[2], created_at=row[3])


def create_session(db: Database, user_id: str) -> SessionGrant:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=8)).isoformat()
    csrf = issue_csrf_token(db)
    with db:
        db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
        db.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), user_id, expires, now.isoformat(), csrf))
    return SessionGrant(token, get_session(db, token))


def get_session(db: Database, cookie_token: str) -> SessionIdentity:
    digest = hashlib.sha256(cookie_token.encode()).hexdigest()
    row = db.execute('SELECT u.id,u.email,u.full_name,u.created_at,p.student_id,s.expires_at,s.last_seen_at,s.csrf_token '
                     'FROM sessions s JOIN users u ON u.id=s.user_id JOIN student_profiles p ON p.user_id=u.id '
                     'WHERE s.token=?', (digest,)).fetchone()
    now = datetime.now(timezone.utc)
    if not row or now >= datetime.fromisoformat(row[5]) or now - datetime.fromisoformat(row[6]) >= timedelta(minutes=30):
        raise ApiProblem(401, 'AUTH_REQUIRED', 'Log in to continue')
    with db:
        db.execute('UPDATE sessions SET last_seen_at=? WHERE token=?', (now.isoformat(), digest))
    user = User(id=row[0], email=row[1], full_name=row[2], created_at=row[3])
    return SessionIdentity(AuthenticatedStudent(row[0], row[4]), SessionResponse(user=user, csrf_token=row[7], expires_at=row[5]))


def revoke_session(db: Database, cookie_token: str) -> None:
    with db:
        db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(cookie_token.encode()).hexdigest(),))


def issue_csrf_token(db: Database) -> str:
    nonce = secrets.token_urlsafe(32)
    signature = hmac.new(session_secret(db), nonce.encode(), hashlib.sha256).hexdigest()
    return f'{nonce}.{signature}'


def validate_csrf_token(db: Database, submitted: str | None, expected: str | None) -> None:
    if submitted and expected and hmac.compare_digest(submitted.encode(), expected.encode()):
        nonce, sep, signature = submitted.partition('.')
        digest = hmac.new(session_secret(db), nonce.encode(), hashlib.sha256).hexdigest()
        if sep and hmac.compare_digest(signature.encode(), digest.encode()):
            return
    raise ApiProblem(403, 'CSRF_FAILED', 'Refresh the page and try again')
