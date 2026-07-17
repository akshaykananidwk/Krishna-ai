"""Token exchange schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserPublic


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    """Returned by register/login — tokens plus the authenticated user."""

    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
