from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas import (
    NotificationCreate,
    NotificationLogOut,
    PreferenceCreate,
    PreferenceOut,
    PreferenceUpdate,
)
from ...services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/preferences", response_model=PreferenceOut, status_code=status.HTTP_201_CREATED)
def create_preference(payload: PreferenceCreate) -> PreferenceOut:
    preference = notification_service.create_preference(payload)
    return PreferenceOut.model_validate(preference)


@router.get("/preferences", response_model=list[PreferenceOut])
def list_preferences(user_id: Optional[int] = Query(None, gt=0)) -> list[PreferenceOut]:
    preferences = notification_service.list_preferences(user_id=user_id)
    return [PreferenceOut.model_validate(pref) for pref in preferences]


@router.put("/preferences/{preference_id}", response_model=PreferenceOut)
def update_preference(preference_id: int, payload: PreferenceUpdate) -> PreferenceOut:
    preference = notification_service.update_preference(preference_id, payload)
    if not preference:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    return PreferenceOut.model_validate(preference)


@router.post("/dispatch", response_model=NotificationLogOut, status_code=status.HTTP_202_ACCEPTED)
def dispatch_notification(payload: NotificationCreate) -> NotificationLogOut:
    log = notification_service.create_notification(payload)
    return NotificationLogOut.model_validate(log)


@router.get("/logs", response_model=list[NotificationLogOut])
def list_notifications(user_id: Optional[int] = Query(None, gt=0)) -> list[NotificationLogOut]:
    logs = notification_service.list_notifications(user_id=user_id)
    return [NotificationLogOut.model_validate(log) for log in logs]
