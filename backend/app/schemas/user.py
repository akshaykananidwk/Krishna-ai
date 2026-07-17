"""User-facing schemas for the authentication module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# A pragmatic password policy: length + basic complexity. Tune per threat model.
_MIN_PASSWORD_LEN = 8
_MAX_PASSWORD_LEN = 128


def _validate_password_strength(value: str) -> str:
    if not any(c.islower() for c in value):
        raise ValueError("Password must contain a lowercase letter.")
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain an uppercase letter.")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain a digit.")
    return value


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_MIN_PASSWORD_LEN, max_length=_MAX_PASSWORD_LEN)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LEN)


class FirebaseLogin(BaseModel):
    """Exchange a Firebase ID token for Krishna AI tokens."""

    id_token: str = Field(min_length=1)


class UserPublic(BaseModel):
    """Safe representation of a user — never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None
