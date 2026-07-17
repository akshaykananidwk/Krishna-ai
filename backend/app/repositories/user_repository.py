"""Repository for :class:`User`, :class:`RefreshToken` and :class:`AuditLog`."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, RefreshToken, User


def hash_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest — what we persist instead of the raw token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class UserRepository:
    """All persistence operations for the authentication module."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---- Users ---------------------------------------------------------- #
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        result = await self._session.execute(select(User).where(User.firebase_uid == firebase_uid))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str | None = None,
        full_name: str | None = None,
        firebase_uid: str | None = None,
        is_verified: bool = False,
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            firebase_uid=firebase_uid,
            is_verified=is_verified,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def touch_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

    # ---- Refresh tokens ------------------------------------------------- #
    async def store_refresh_token(
        self, *, user_id: uuid.UUID, raw_token: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_active_refresh_token(self, raw_token: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
        )
        token = result.scalar_one_or_none()
        if token is None or not token.is_active:
            return None
        return token

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        now = datetime.now(UTC)
        for token in result.scalars():
            token.revoked_at = now
        await self._session.flush()

    # ---- Audit log ------------------------------------------------------ #
    async def add_audit_log(
        self,
        *,
        action: str,
        user_id: uuid.UUID | None = None,
        detail: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                user_id=user_id,
                action=action,
                detail=detail,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await self._session.flush()
