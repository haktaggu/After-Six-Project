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
