import secrets
import string
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..core.database import session_scope
from ..models import User
from ..schemas import UserCreate, UserUpdate


def generate_access_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class UserService:
    """Business logic for managing users."""

    def create_user(self, payload: UserCreate) -> User:
        new_code = payload.access_code or generate_access_code()
        with session_scope() as session:
            user = User(
                full_name=payload.full_name,
                email=payload.email,
                role=payload.role,
                telegram_id=payload.telegram_id,
                access_code=new_code,
            )
            session.add(user)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("User with given email or telegram already exists") from exc
            session.refresh(user)
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        with session_scope() as session:
            return session.get(User, user_id)

    def get_users(self) -> List[User]:
        with session_scope() as session:
            return list(session.scalars(select(User).order_by(User.created_at.desc())))

    def find_by_telegram(self, telegram_id: str) -> Optional[User]:
        with session_scope() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            return session.scalars(stmt).first()

    def update_user(self, user_id: int, payload: UserUpdate) -> Optional[User]:
        with session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return None

            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            session.add(user)
            session.flush()
            session.refresh(user)
            return user

    def deactivate_user(self, user_id: int) -> bool:
        with session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            user.is_active = False
            session.add(user)
            return True


user_service = UserService()
