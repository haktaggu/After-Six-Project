from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import AuthenticatedStudent, Database, Notification, NotificationPreferences, Page, PreferencesUpdate
from app.features.notifications import discord_available

# - Read notification_preferences(student_id PK/FK profiles,enabled INTEGER DEFAULT 0).
# - No row means enabled=False. Return {enabled: bool, available: discord_available()}.
# - Read only student.student_id; do not include the backend Discord URL in the response.
def get_preferences(db: Database, student: AuthenticatedStudent) -> NotificationPreferences:
    raise NotImplementedError


# - PATCH body is {enabled: bool}; no field omission or null is allowed.
# - Enabling without a configured provider raises ApiProblem(503,"CHANNEL_UNAVAILABLE",...).
# - Upsert the current student's enabled flag using parameters in one transaction; commit.
# - Disabling works even when Discord is unavailable. Return get_preferences after saving.
def update_preferences(db: Database, student: AuthenticatedStudent, body: PreferencesUpdate) -> NotificationPreferences:
    raise NotImplementedError


# - Read only the current student's notification_logs; count before paging.
# - Validate limit 1..100, offset >=0; defaults 25/0. Sort created_at DESC then ID ASC.
# - Return Page[Notification] with items containing id,section_id,event_type="section_opened",
#   status pending/sent/failed,created_at UTC,sent_at UTC or None. Empty history is items=[].
# - Storage: notification_logs(id TEXT UUID PK,event_id FK availability_events,student_id FK
#   profiles,section_id FK sections,event_type,message,status,created_at,sent_at,last_error;
#   UNIQUE(event_id,student_id)). Message and last_error are private; reads do not commit.
def list_notifications(db: Database, student: AuthenticatedStudent, limit: int = 25, offset: int = 0) -> Page[Notification]:
    raise NotImplementedError
