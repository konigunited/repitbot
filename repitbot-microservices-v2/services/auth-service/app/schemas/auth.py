from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CredentialCreate(BaseModel):
    user_id: int = Field(gt=0)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str


class CredentialUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=8)
    role: Optional[str] = None


class CredentialOut(BaseModel):
    user_id: int
    email: EmailStr
    role: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
