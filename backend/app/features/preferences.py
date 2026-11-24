from __future__ import annotations

from app.errors import ApiProblem
from app.features import notification_providers
from app.features.notifications import discord_available
from app.schemas import AuthenticatedStudent, Database, Notification, NotificationPreferences, Page, PreferencesUpdate


def get_preferences(db: Database, student: AuthenticatedStudent) -> NotificationPreferences:
    row = db.execute('SELECT enabled, webhook_url FROM notification_preferences WHERE student_id=?', (student.student_id,)).fetchone()
    webhook = row[1] if row and len(row) > 1 else None
    return NotificationPreferences(enabled=bool(row and row[0]), available=True, webhook_url=webhook)


def update_preferences(db: Database, student: AuthenticatedStudent, body: PreferencesUpdate) -> NotificationPreferences:
    webhook = (body.webhook_url or '').strip() or None
    if webhook and not notification_providers.valid_destination(webhook):
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Please enter a valid Discord webhook URL (e.g. https://discord.com/api/webhooks/...)')
    if body.enabled and not webhook and not discord_available():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Please enter a Discord webhook URL to enable Discord alerts.')
    with db:
        db.execute('INSERT INTO notification_preferences (student_id,enabled,webhook_url) VALUES (?,?,?) '
                   'ON CONFLICT(student_id) DO UPDATE SET enabled=excluded.enabled, webhook_url=excluded.webhook_url',
                   (student.student_id, int(body.enabled), webhook))
    return get_preferences(db, student)


def list_notifications(
    db: Database,
    student: AuthenticatedStudent,
    limit: int = 25,
    offset: int = 0,
) -> Page[Notification]:
    total = db.execute(
        "SELECT count(*) FROM notification_logs WHERE student_id=?",
        (student.student_id,),
    ).fetchone()[0]

    rows = db.execute(
        """
        SELECT id, section_id, event_type, status, created_at, sent_at, is_read
        FROM notification_logs
        WHERE student_id=?
        ORDER BY created_at DESC, id
        LIMIT ? OFFSET ?
        """,
        (student.student_id, limit, offset),
    )

    return Page(
        items=[
            Notification(
                id=row[0],
                section_id=row[1],
                event_type=row[2],
                status=row[3],
                created_at=row[4],
                sent_at=row[5],
                is_read=bool(row[6]),
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )

def mark_notification_read(
    db: Database,
    student: AuthenticatedStudent,
    notification_id: str,
) -> None:
    with db:
        cursor = db.execute(
            """
            UPDATE notification_logs
            SET is_read=1
            WHERE id=? AND student_id=?
            """,
            (notification_id, student.student_id),
        )

        if cursor.rowcount == 0:
            raise ApiProblem(
                404,
                "NOTIFICATION_NOT_FOUND",
                "Notification was not found.",
            )
