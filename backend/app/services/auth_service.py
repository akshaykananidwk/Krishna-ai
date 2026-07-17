"""Authentication business logic (Module 1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.token import AuthResponse, TokenPair
from app.schemas.user import UserPublic

# A valid bcrypt hash of a random value. Verified against on the "user not found"
# path so login timing does not reveal whether an email is registered.
_DUMMY_PASSWORD_HASH = "$2b$12$SeljY2WozFJkdCzWClyIEeqvEGIj6FPGBnxpgsDhzBvDHwfplaZn."


class AuthService:
    """Registration, login, token refresh and logout."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    # ---- helpers -------------------------------------------------------- #
    async def _issue_tokens(self, user: User) -> TokenPair:
        access = create_access_token(str(user.id), extra_claims={"email": user.email})
        refresh = create_refresh_token(str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._repo.store_refresh_token(
            user_id=user.id, raw_token=refresh, expires_at=expires_at
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    @staticmethod
    def _to_response(tokens: TokenPair, user: User) -> AuthResponse:
        return AuthResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            user=UserPublic.model_validate(user),
        )

    # ---- use cases ------------------------------------------------------ #
    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        request_meta: dict[str, str | None] | None = None,
    ) -> AuthResponse:
        if await self._repo.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError()

        user = await self._repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await self._repo.touch_last_login(user)
        tokens = await self._issue_tokens(user)
        await self._audit("register", user.id, request_meta)
        return self._to_response(tokens, user)

    async def login(
        self,
        *,
        email: str,
        password: str,
        request_meta: dict[str, str | None] | None = None,
    ) -> AuthResponse:
        user = await self._repo.get_by_email(email)
        # Verify against a real-looking hash even when the user is missing to
        # avoid a timing side-channel that reveals which emails are registered.
        stored_hash = (
            user.hashed_password if user and user.hashed_password else _DUMMY_PASSWORD_HASH
        )
        password_ok = verify_password(password, stored_hash)

        if user is None or not password_ok:
            await self._audit("login_failed", user.id if user else None, request_meta, detail=email)
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()

        await self._repo.touch_last_login(user)
        tokens = await self._issue_tokens(user)
        await self._audit("login", user.id, request_meta)
        return self._to_response(tokens, user)

    async def refresh(
        self,
        *,
        refresh_token: str,
        request_meta: dict[str, str | None] | None = None,
    ) -> TokenPair:
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError() from exc

        stored = await self._repo.get_active_refresh_token(refresh_token)
        if stored is None:
            raise InvalidTokenError("Refresh token has been revoked or is unknown.")

        user = await self._repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError()

        # Rotate: revoke the presented token and issue a fresh pair.
        await self._repo.revoke_refresh_token(stored)
        tokens = await self._issue_tokens(user)
        await self._audit("token_refresh", user.id, request_meta)
        assert payload["sub"] == str(user.id)
        return tokens

    async def logout(
        self,
        *,
        refresh_token: str,
        request_meta: dict[str, str | None] | None = None,
    ) -> None:
        stored = await self._repo.get_active_refresh_token(refresh_token)
        if stored is not None:
            await self._repo.revoke_refresh_token(stored)
            await self._audit("logout", stored.user_id, request_meta)

    # ---- audit ---------------------------------------------------------- #
    async def _audit(
        self,
        action: str,
        user_id,
        request_meta: dict[str, str | None] | None,
        detail: str | None = None,
    ) -> None:
        meta = request_meta or {}
        await self._repo.add_audit_log(
            action=action,
            user_id=user_id,
            detail=detail,
            ip_address=meta.get("ip_address"),
            user_agent=meta.get("user_agent"),
        )
