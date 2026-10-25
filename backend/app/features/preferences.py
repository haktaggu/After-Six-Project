from __future__ import annotations

from app.errors import ApiProblem
from app.features.notifications import discord_available
from app.schemas import AuthenticatedStudent, Database, Notification, NotificationPreferences, Page, PreferencesUpdate


def get_preferences(db: Database, student: AuthenticatedStudent) -> NotificationPreferences:
    row = db.execute('SELECT enabled FROM notification_preferences WHERE student_id=?', (student.student_id,)).fetchone()
    return NotificationPreferences(enabled=bool(row and row[0]), available=discord_available())


def update_preferences(db: Database, student: AuthenticatedStudent, body: PreferencesUpdate) -> NotificationPreferences:
    if body.enabled and not discord_available():
        raise ApiProblem(503, 'CHANNEL_UNAVAILABLE', 'Discord alerts are not configured. You can still save watches.')
    with db:
        db.execute('INSERT INTO notification_preferences (student_id,enabled) VALUES (?,?) '
                   'ON CONFLICT(student_id) DO UPDATE SET enabled=excluded.enabled', (student.student_id, int(body.enabled)))
    return get_preferences(db, student)


def list_notifications(db: Database, student: AuthenticatedStudent, limit: int = 25, offset: int = 0) -> Page[Notification]:
    total = db.execute('SELECT count(*) FROM notification_logs WHERE student_id=?', (student.student_id,)).fetchone()[0]
    rows = db.execute('SELECT id,section_id,event_type,status,created_at,sent_at FROM notification_logs WHERE student_id=? '
                      'ORDER BY created_at DESC,id LIMIT ? OFFSET ?', (student.student_id, limit, offset))
    return Page(items=[Notification(**dict(zip(('id', 'section_id', 'event_type', 'status', 'created_at', 'sent_at'), r))) for r in rows], total=total, limit=limit, offset=offset)
