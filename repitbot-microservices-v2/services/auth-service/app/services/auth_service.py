from datetime import datetime, timedelta
import hashlib

from jose import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..core.config import get_settings
from ..core.database import session_scope
from ..models import Credential
from ..schemas import CredentialCreate, CredentialOut, CredentialUpdate, LoginRequest, TokenResponse

settings = get_settings()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class AuthService:
    """Authentication logic: credentials storage and token issuing."""

    def register(self, payload: CredentialCreate) -> Credential:
        with session_scope() as session:
            credential = Credential(
                user_id=payload.user_id,
                email=payload.email.lower(),
                password_hash=_hash_password(payload.password),
                role=payload.role,
            )
            session.add(credential)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("Credentials already exist for this user") from exc
            session.refresh(credential)
            return credential

    def update(self, user_id: int, payload: CredentialUpdate) -> Credential | None:
        with session_scope() as session:
            credential = session.scalars(select(Credential).where(Credential.user_id == user_id)).first()
            if not credential:
                return None
            update_data = payload.model_dump(exclude_unset=True)
            if "password" in update_data:
                credential.password_hash = _hash_password(update_data.pop("password"))
            for field, value in update_data.items():
                setattr(credential, field, value)
            session.add(credential)
            session.flush()
            session.refresh(credential)
            return credential

    def authenticate(self, payload: LoginRequest) -> TokenResponse:
        with session_scope() as session:
            credential = session.scalars(
                select(Credential).where(Credential.email == payload.email.lower())
            ).first()
            if not credential:
                raise ValueError("Invalid credentials")
            if credential.password_hash != _hash_password(payload.password):
                raise ValueError("Invalid credentials")
            credential.last_login_at = datetime.utcnow()
            session.add(credential)
            session.flush()
            session.refresh(credential)

        expires_in = settings.jwt_expiration_minutes * 60
        expiration = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
        token = jwt.encode(
            {
                "sub": str(credential.user_id),
                "role": credential.role,
                "exp": expiration,
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        return TokenResponse(access_token=token, expires_in=expires_in)

    def get_credentials(self, user_id: int) -> Credential | None:
        with session_scope() as session:
            return session.scalars(select(Credential).where(Credential.user_id == user_id)).first()


auth_service = AuthService()
