from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.common import DatabaseDep, StudentDep, require_csrf
from app.schemas import Notification, NotificationPreferences, Page, PaginationQuery, PreferencesUpdate
from app.features import preferences

router = APIRouter(prefix="/api")

# - Return {enabled: bool, available: bool}; the Discord webhook stays on the server.
@router.get("/me/notification-preferences", response_model=NotificationPreferences)
def preferences_get(db: DatabaseDep, student: StudentDep) -> NotificationPreferences:
    return preferences.get_preferences(db, student)

# - Body is {enabled: bool}; enabling without a configured provider returns 503.
@router.patch("/me/notification-preferences", response_model=NotificationPreferences, dependencies=[Depends(require_csrf)])
def preferences_patch(body: PreferencesUpdate, db: DatabaseDep, student: StudentDep) -> NotificationPreferences:
    return preferences.update_preferences(db, student, body)

# - Return the current student's history, created_at DESC then ID ASC.
@router.get("/me/notifications", response_model=Page[Notification])
def history(db: DatabaseDep, student: StudentDep, query: Annotated[PaginationQuery, Query()]) -> Page[Notification]:
    return preferences.list_notifications(db, student, query.limit, query.offset)
