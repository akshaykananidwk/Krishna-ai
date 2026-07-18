"""Background maintenance jobs for the Memory Engine.

The core jobs take their dependencies explicitly so they are unit-testable and
transport-agnostic. Thin ``run_*`` wrappers open a real DB session + the
configured vector store for production use (FastAPI background task, cron, or a
Celery/RQ worker).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.memory import MemoryStatus
from app.repositories.memory_repository import MemoryRepository
from app.services.embeddings.factory import build_embedding_provider
from app.services.memory.memory_service import MemoryService
from app.services.vectorstore.base import VectorStore
from app.services.vectorstore.factory import build_vector_store


@dataclass
class MaintenanceReport:
    purged: int = 0
    retried: int = 0
    reindexed: int = 0


# --------------------------------------------------------------------------- #
# Core jobs (explicit dependencies)
# --------------------------------------------------------------------------- #
async def cleanup_deleted(repo: MemoryRepository, vector_store: VectorStore) -> int:
    """Hard-delete soft-deleted memories past the retention window."""
    ids = await repo.hard_delete_expired(retention_days=settings.MEMORY_RETENTION_DAYS)
    if ids:
        await vector_store.delete([str(i) for i in ids])
    return len(ids)


async def retry_failed_embeddings(
    repo: MemoryRepository, service: MemoryService, *, limit: int = 100
) -> int:
    """Re-attempt embeddings that previously failed."""
    failed = await repo.failed_embeddings(limit=limit)
    count = 0
    for embedding in failed:
        item = await repo.get_item_by_id(embedding.memory_id)
        if item is None:
            continue
        await service.embed_memory(item)
        count += 1
    return count


async def reindex_user(repo: MemoryRepository, service: MemoryService, user_id: uuid.UUID) -> int:
    """Re-embed all active memories for a user (e.g. after switching provider)."""
    items = await repo.list_items(user_id=user_id, status=MemoryStatus.ACTIVE, limit=10_000)
    for item in items:
        await service.embed_memory(item)
    return len(items)


# --------------------------------------------------------------------------- #
# Production wrappers (own their session + configured dependencies)
# --------------------------------------------------------------------------- #
def _build(session) -> tuple[MemoryRepository, MemoryService, VectorStore]:
    repo = MemoryRepository(session)
    store = build_vector_store()
    service = MemoryService(repo, build_embedding_provider(), store)
    return repo, service, store


async def run_cleanup() -> int:
    async with AsyncSessionLocal() as session:
        repo, _, store = _build(session)
        n = await cleanup_deleted(repo, store)
        await session.commit()
        return n


async def run_retry_failed() -> int:
    async with AsyncSessionLocal() as session:
        repo, service, _ = _build(session)
        n = await retry_failed_embeddings(repo, service)
        await session.commit()
        return n


async def run_reindex_user(user_id: uuid.UUID) -> int:
    async with AsyncSessionLocal() as session:
        repo, service, _ = _build(session)
        n = await reindex_user(repo, service, user_id)
        await session.commit()
        return n


async def run_all_maintenance() -> MaintenanceReport:
    return MaintenanceReport(
        purged=await run_cleanup(),
        retried=await run_retry_failed(),
    )
