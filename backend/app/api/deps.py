"""Reusable FastAPI dependencies (DB session, current user, request metadata)."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import InactiveUserError, InvalidTokenError
from app.core.security import TokenType, decode_token
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.llm.anthropic_client import AnthropicLLMClient
from app.services.llm.base import LLMClient

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_auth_service(repo: UserRepositoryDep) -> AuthService:
    return AuthService(repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# A single LLM client is shared across requests (it lazily creates the SDK
# client and holds no per-request state). Tests override this dependency.
_llm_client: LLMClient = AnthropicLLMClient()


def get_llm_client() -> LLMClient:
    return _llm_client


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]


def get_chat_service(db: DbSession, llm: LLMClientDep) -> ChatService:
    return ChatService(ChatRepository(db), llm)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def get_request_meta(request: Request) -> dict[str, str | None]:
    """Extract client IP and user-agent for audit logging."""
    client = request.client
    return {
        "ip_address": client.host if client else None,
        "user_agent": request.headers.get("user-agent"),
    }


RequestMeta = Annotated[dict[str, str | None], Depends(get_request_meta)]


async def get_current_user(
    repo: UserRepositoryDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Resolve and validate the bearer access token into a live ``User``."""
    if credentials is None:
        raise InvalidTokenError("Missing bearer token.")
    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc

    import uuid

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError() from exc

    user = await repo.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError()
    if not user.is_active:
        raise InactiveUserError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
