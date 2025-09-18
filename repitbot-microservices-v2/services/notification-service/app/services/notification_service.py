from typing import List, Optional

from sqlalchemy import select

from ..core.database import session_scope
from ..models import NotificationChannel, NotificationLog, NotificationPreference
from ..schemas import (
    NotificationCreate,
    NotificationLogOut,
    PreferenceCreate,
    PreferenceOut,
    PreferenceUpdate,
)


class NotificationService:
    """Business logic for notification preferences and dispatch logs."""

    def create_preference(self, payload: PreferenceCreate) -> NotificationPreference:
        with session_scope() as session:
            preference = NotificationPreference(**payload.model_dump())
            session.add(preference)
            session.flush()
            session.refresh(preference)
            return preference

    def update_preference(self, preference_id: int, payload: PreferenceUpdate) -> Optional[NotificationPreference]:
        with session_scope() as session:
            preference = session.get(NotificationPreference, preference_id)
            if not preference:
                return None
            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(preference, field, value)
            session.add(preference)
            session.flush()
            session.refresh(preference)
            return preference

    def list_preferences(self, user_id: Optional[int] = None) -> List[NotificationPreference]:
        with session_scope() as session:
            stmt = select(NotificationPreference)
            if user_id:
                stmt = stmt.where(NotificationPreference.user_id == user_id)
            return list(session.scalars(stmt))

    def create_notification(self, payload: NotificationCreate) -> NotificationLog:
        with session_scope() as session:
            log = NotificationLog(
                user_id=payload.user_id,
                channel=payload.channel,
                payload=payload.message,
                status="queued",
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            return log

    def list_notifications(self, user_id: Optional[int] = None) -> List[NotificationLog]:
        with session_scope() as session:
            stmt = select(NotificationLog)
            if user_id:
                stmt = stmt.where(NotificationLog.user_id == user_id)
            stmt = stmt.order_by(NotificationLog.created_at.desc())
            return list(session.scalars(stmt))


notification_service = NotificationService()
