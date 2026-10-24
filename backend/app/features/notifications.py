from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import Database, DeliveryResult, DeliveryTarget, SeatOpeningEvent
from app.features import notification_providers

# - Read DISCORD_WEBHOOK_URL without making a network request.
# - Return True only for a nonempty HTTPS URL on discord.com with /api/webhooks/<id>/<token>.
#   Reject URL credentials, query strings, fragments and a nonstandard port.
# - Missing or invalid configuration returns False. The provider checks public DNS/IP at send time.
def discord_available() -> bool:
    raise NotImplementedError


# - event has id,section_id,previous_seats=0,new_seats>0,detected_at (UTC ISO 8601).
# - In a short transaction, read the persisted availability_events row. Missing ->404;
#   processed_at already set ->return 0. Use the stored event values, not caller overrides.
# - Find active watchlists joined to enabled notification_preferences for that section.
# - Insert one pending notification_logs row per matching student, with a UUID delivery ID,
#   event_type=section_opened, a readable message and created_at UTC. UNIQUE(event_id,student_id)
#   prevents duplicate rows. Include section/course details in the message, not a webhook URL.
# - Set availability_events.processed_at only in the same transaction as those inserts; commit
#   and return the inserted count. A disabled/unwatched student gets no delivery.
# - No network here. The automatic worker is the one dispatcher; no leases or failed-send retries.
def dispatch_opening_event(db: Database, event: SeatOpeningEvent) -> int:
    raise NotImplementedError


# - target has delivery_id,event_id,student_id,section_id,message. Read its persisted log first.
# - Only a pending row may be sent. Sent/failed rows return their stored DeliveryResult without
#   another request. A missing delivery raises 404 NOT_FOUND.
# - Read DISCORD_WEBHOOK_URL and call send_discord(url,message,delivery_id) outside any write
#   transaction. Missing/invalid configuration yields accepted=False with a safe error code.
# - In a short transaction set status=sent and sent_at=UTC only on acceptance. Otherwise set
#   status=failed, sent_at=None and last_error to a redacted code; commit and return the result.
# - DeliveryResult is {accepted: bool,error_code: str | None}. Keep URL/token out of logs/errors.
# - A failed send stays failed. Isolate one delivery's failure from other students/events.
#   A crash after provider acceptance can duplicate a still-pending delivery on a later run.
def deliver_notification(db: Database, target: DeliveryTarget) -> DeliveryResult:
    raise NotImplementedError
