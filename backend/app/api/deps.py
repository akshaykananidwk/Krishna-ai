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
from app.repositories.memory_repository import MemoryRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.factory import build_embedding_provider
from app.services.llm.anthropic_client import AnthropicLLMClient
from app.services.llm.base import LLMClient
from app.services.memory.memory_service import MemoryService
from app.services.memory.rag_service import RagService
from app.services.vectorstore.base import VectorStore
from app.services.vectorstore.factory import build_vector_store

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


# ---- Memory Engine (Module 4) ---- #
# Embedding provider and vector store are process-wide (stateless / singleton);
# tests override these dependencies with a local embedder + fresh in-memory store.
_embedding_provider: EmbeddingProvider = build_embedding_provider()
_vector_store: VectorStore = build_vector_store()


def get_embedding_provider() -> EmbeddingProvider:
    return _embedding_provider


def get_vector_store() -> VectorStore:
    return _vector_store


EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]


def get_memory_service(
    db: DbSession,
    embeddings: EmbeddingProviderDep,
    vector_store: VectorStoreDep,
) -> MemoryService:
    return MemoryService(MemoryRepository(db), embeddings, vector_store)


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]


def get_rag_service(memory: MemoryServiceDep, llm: LLMClientDep) -> RagService:
    return RagService(memory, llm)


RagServiceDep = Annotated[RagService, Depends(get_rag_service)]


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
