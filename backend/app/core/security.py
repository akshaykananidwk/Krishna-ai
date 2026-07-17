"""Security primitives: password hashing and JWT token handling.

This module deliberately contains *no* framework/HTTP concerns — it is pure
cryptography and token logic so it can be unit-tested in isolation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from app.core.config import settings
from passlib.context import CryptContext

# bcrypt with a sane default work factor.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash of ``plain_password``."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification of a password against its hash."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Malformed hash in storage — never leak the reason to the caller.
        return False


# --------------------------------------------------------------------------- #
# JWT tokens
# --------------------------------------------------------------------------- #
def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT.

    Raises ``jwt.InvalidTokenError`` (or a subclass) on any failure, including a
    type mismatch when ``expected_type`` is provided.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError(
            f"Expected {expected_type.value} token, got {payload.get('type')!r}"
        )
    return payload
