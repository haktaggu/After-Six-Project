from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import uuid4

from app.errors import ApiProblem
from app.features import notification_providers
from app.schemas import Database, DeliveryResult, DeliveryTarget, SeatOpeningEvent


def discord_available() -> bool:
    return notification_providers.valid_destination(os.environ.get('DISCORD_WEBHOOK_URL', ''))


def dispatch_opening_event(db: Database, event: SeatOpeningEvent) -> int:
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT section_id,new_seats,processed_at FROM availability_events WHERE id=?', (event.id,)).fetchone()
        if not row:
            raise ApiProblem(404, 'NOT_FOUND', 'Opening event not found')
        if row[2]:
            return 0
        section = db.execute('SELECT c.id,c.title,s.section_number,s.source_url FROM sections s JOIN courses c ON c.id=s.course_id WHERE s.id=?', (row[0],)).fetchone()
        students = db.execute('SELECT w.student_id FROM watchlists w JOIN notification_preferences p ON p.student_id=w.student_id '
                              'WHERE w.section_id=? AND w.active=1 AND p.enabled=1', (row[0],)).fetchall()
        now = datetime.now(timezone.utc).isoformat()
        message = f'{section[0]} — {section[1]}, section {section[2]}: {row[1]} open seat(s) observed. Check MySJSU before enrolling. {section[3]}'
        count = 0
        for student in students:
            cur = db.execute('INSERT INTO notification_logs (id,event_id,student_id,section_id,event_type,message,status,created_at) '
                             "VALUES (?,?,?,?,'section_opened',?,'pending',?) ON CONFLICT(event_id,student_id) DO NOTHING",
                             (str(uuid4()), event.id, student[0], row[0], message, now))
            count += cur.rowcount
        db.execute('UPDATE availability_events SET processed_at=? WHERE id=?', (now, event.id))
    return count


def deliver_notification(db: Database, target: DeliveryTarget) -> DeliveryResult:
    row = db.execute('SELECT status,message,last_error FROM notification_logs WHERE id=?', (target.delivery_id,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Delivery not found')
    if row[0] != 'pending':
        return DeliveryResult(accepted=row[0] == 'sent', error_code=row[2])
    result = notification_providers.send_discord(os.environ.get('DISCORD_WEBHOOK_URL', ''), row[1], target.delivery_id)
    with db:
        db.execute('UPDATE notification_logs SET status=?,sent_at=?,last_error=? WHERE id=? AND status=?',
                   ('sent' if result.accepted else 'failed', datetime.now(timezone.utc).isoformat() if result.accepted else None,
                    result.error_code, target.delivery_id, 'pending'))
    return result
