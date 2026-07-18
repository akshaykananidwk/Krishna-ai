"""Tests for the Memory Engine background maintenance jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.core.security import hash_password
from app.models.memory import EmbeddingStatus, MemorySourceType, MemoryStatus
from app.models.user import User
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import MemoryCreate
from app.services.embeddings.local import LocalEmbeddingProvider
from app.services.memory.maintenance import (
    cleanup_deleted,
    retry_failed_embeddings,
)
from app.services.memory.memory_service import MemoryService
from app.services.vectorstore.memory import InMemoryVectorStore


@pytest_asyncio.fixture
async def user(db_session) -> User:
    u = User(email="worker@example.com", hashed_password=hash_password("Dharma123"))
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
def service(db_session):
    repo = MemoryRepository(db_session)
    return MemoryService(repo, LocalEmbeddingProvider(dim=128), InMemoryVectorStore())


@pytest.mark.asyncio
async def test_cleanup_purges_expired_deleted(db_session, user, service):
    repo = MemoryRepository(db_session)
    item = await service.create_memory(
        user_id=user.id,
        payload=MemoryCreate(content="expiring memory to purge", source_type="note"),
    )
    await repo.set_status(item, MemoryStatus.DELETED)
    # Backdate deletion beyond the retention window.
    item.deleted_at = datetime.now(UTC) - timedelta(days=60)
    await db_session.flush()

    purged = await cleanup_deleted(repo, service._vs)
    assert purged == 1
    assert await repo.get_item_by_id(item.id) is None


@pytest.mark.asyncio
async def test_cleanup_keeps_recent_deleted(db_session, user, service):
    repo = MemoryRepository(db_session)
    item = await service.create_memory(
        user_id=user.id,
        payload=MemoryCreate(content="recently deleted", source_type="note"),
    )
    await repo.set_status(item, MemoryStatus.DELETED)  # deleted_at = now
    purged = await cleanup_deleted(repo, service._vs)
    assert purged == 0
    assert await repo.get_item_by_id(item.id) is not None


@pytest.mark.asyncio
async def test_retry_failed_embeddings_recovers(db_session, user, service):
    repo = MemoryRepository(db_session)
    item = await repo.create_item(
        user_id=user.id,
        content="a memory whose embedding failed",
        title=None,
        source_type=MemorySourceType.NOTE,
        source_ref=None,
        importance=0.5,
        pinned=False,
    )
    await repo.upsert_embedding(
        memory_id=item.id,
        provider="local",
        model="x",
        dim=128,
        vector_id=str(item.id),
        status=EmbeddingStatus.FAILED,
        error="boom",
    )

    retried = await retry_failed_embeddings(repo, service, limit=10)
    assert retried == 1

    remaining = await repo.failed_embeddings(limit=10)
    assert remaining == []
