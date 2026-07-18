"""Persistence for the Memory Engine (PostgreSQL is the source of truth)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import (
    EmbeddingStatus,
    KnowledgeSource,
    MemoryBookmark,
    MemoryCollection,
    MemoryCollectionItem,
    MemoryEmbedding,
    MemoryFeedback,
    MemoryItem,
    MemoryLink,
    MemoryMetadata,
    MemorySearchLog,
    MemorySourceType,
    MemoryStatus,
    MemoryTag,
)


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---- items ---------------------------------------------------------- #
    async def create_item(
        self,
        *,
        user_id: uuid.UUID,
        content: str,
        title: str | None,
        source_type: MemorySourceType,
        source_ref: str | None,
        importance: float,
        pinned: bool,
    ) -> MemoryItem:
        item = MemoryItem(
            user_id=user_id,
            content=content,
            title=title,
            source_type=source_type,
            source_ref=source_ref,
            importance=importance,
            pinned=pinned,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_item(self, *, item_id: uuid.UUID, user_id: uuid.UUID) -> MemoryItem | None:
        result = await self._session.execute(
            select(MemoryItem).where(MemoryItem.id == item_id, MemoryItem.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_item_by_id(self, item_id: uuid.UUID) -> MemoryItem | None:
        """Fetch without user scoping (maintenance workers only)."""
        return await self._session.get(MemoryItem, item_id)

    async def list_items(
        self,
        *,
        user_id: uuid.UUID,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        source_type: MemorySourceType | None = None,
        pinned: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryItem]:
        stmt = select(MemoryItem).where(MemoryItem.user_id == user_id, MemoryItem.status == status)
        if source_type is not None:
            stmt = stmt.where(MemoryItem.source_type == source_type)
        if pinned is not None:
            stmt = stmt.where(MemoryItem.pinned == pinned)
        stmt = stmt.order_by(MemoryItem.created_at.desc()).limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars().all())

    async def items_by_ids(
        self, *, ids: Sequence[uuid.UUID], user_id: uuid.UUID
    ) -> dict[uuid.UUID, MemoryItem]:
        if not ids:
            return {}
        result = await self._session.execute(
            select(MemoryItem).where(MemoryItem.id.in_(ids), MemoryItem.user_id == user_id)
        )
        return {item.id: item for item in result.scalars().all()}

    async def touch_access(self, items: Sequence[MemoryItem]) -> None:
        now = datetime.now(UTC)
        for item in items:
            item.access_count += 1
            item.last_accessed_at = now
        await self._session.flush()

    async def set_status(self, item: MemoryItem, status: MemoryStatus) -> None:
        item.status = status
        now = datetime.now(UTC)
        item.archived_at = now if status == MemoryStatus.ARCHIVED else None
        item.deleted_at = now if status == MemoryStatus.DELETED else None
        await self._session.flush()

    async def hard_delete_expired(self, *, retention_days: int) -> list[uuid.UUID]:
        """Purge soft-deleted items older than the retention window; return ids."""
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        result = await self._session.execute(
            select(MemoryItem.id).where(
                MemoryItem.status == MemoryStatus.DELETED,
                MemoryItem.deleted_at < cutoff,
            )
        )
        ids = [row[0] for row in result.all()]
        if ids:
            await self._session.execute(delete(MemoryItem).where(MemoryItem.id.in_(ids)))
            await self._session.flush()
        return ids

    # ---- embeddings ----------------------------------------------------- #
    async def upsert_embedding(
        self,
        *,
        memory_id: uuid.UUID,
        provider: str,
        model: str,
        dim: int,
        vector_id: str,
        status: EmbeddingStatus,
        error: str | None = None,
    ) -> MemoryEmbedding:
        existing = (
            await self._session.execute(
                select(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory_id)
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = MemoryEmbedding(memory_id=memory_id, vector_id=vector_id, dim=dim)
            self._session.add(existing)
        existing.provider = provider
        existing.model = model
        existing.dim = dim
        existing.vector_id = vector_id
        existing.status = status
        existing.error = error
        existing.attempts = (existing.attempts or 0) + 1
        await self._session.flush()
        return existing

    async def failed_embeddings(self, *, limit: int) -> list[MemoryEmbedding]:
        result = await self._session.execute(
            select(MemoryEmbedding)
            .where(MemoryEmbedding.status == EmbeddingStatus.FAILED)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ---- tags ----------------------------------------------------------- #
    async def add_tags(
        self, *, memory_id: uuid.UUID, tags: Sequence[str], source: str = "manual"
    ) -> None:
        existing = {
            row[0]
            for row in (
                await self._session.execute(
                    select(MemoryTag.tag).where(MemoryTag.memory_id == memory_id)
                )
            ).all()
        }
        for tag in tags:
            normalized = tag.strip().lower()
            if normalized and normalized not in existing:
                self._session.add(MemoryTag(memory_id=memory_id, tag=normalized, source=source))
                existing.add(normalized)
        await self._session.flush()

    async def remove_tag(self, *, memory_id: uuid.UUID, tag: str) -> None:
        await self._session.execute(
            delete(MemoryTag).where(
                MemoryTag.memory_id == memory_id, MemoryTag.tag == tag.strip().lower()
            )
        )
        await self._session.flush()

    # ---- bookmarks ------------------------------------------------------ #
    async def toggle_bookmark(self, *, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        existing = (
            await self._session.execute(
                select(MemoryBookmark).where(
                    MemoryBookmark.user_id == user_id,
                    MemoryBookmark.memory_id == memory_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()
            return False
        self._session.add(MemoryBookmark(user_id=user_id, memory_id=memory_id))
        await self._session.flush()
        return True

    # ---- feedback ------------------------------------------------------- #
    async def set_feedback(self, *, user_id: uuid.UUID, memory_id: uuid.UUID, signal: int) -> None:
        existing = (
            await self._session.execute(
                select(MemoryFeedback).where(
                    MemoryFeedback.user_id == user_id,
                    MemoryFeedback.memory_id == memory_id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self._session.add(MemoryFeedback(user_id=user_id, memory_id=memory_id, signal=signal))
        else:
            existing.signal = signal
        await self._session.flush()

    async def feedback_totals(self, *, memory_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not memory_ids:
            return {}
        result = await self._session.execute(
            select(MemoryFeedback.memory_id, func.sum(MemoryFeedback.signal))
            .where(MemoryFeedback.memory_id.in_(memory_ids))
            .group_by(MemoryFeedback.memory_id)
        )
        return {row[0]: int(row[1] or 0) for row in result.all()}

    # ---- links / dedupe ------------------------------------------------- #
    async def add_link(
        self,
        *,
        user_id: uuid.UUID,
        source_memory_id: uuid.UUID,
        target_memory_id: uuid.UUID,
        link_type: str,
        score: float | None,
    ) -> None:
        self._session.add(
            MemoryLink(
                user_id=user_id,
                source_memory_id=source_memory_id,
                target_memory_id=target_memory_id,
                link_type=link_type,
                score=score,
            )
        )
        await self._session.flush()

    # ---- metadata (encrypted) ------------------------------------------- #
    async def set_metadata(self, *, memory_id: uuid.UUID, key: str, value_encrypted: str) -> None:
        existing = (
            await self._session.execute(
                select(MemoryMetadata).where(
                    MemoryMetadata.memory_id == memory_id, MemoryMetadata.key == key
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self._session.add(
                MemoryMetadata(memory_id=memory_id, key=key, value_encrypted=value_encrypted)
            )
        else:
            existing.value_encrypted = value_encrypted
        await self._session.flush()

    # ---- collections ---------------------------------------------------- #
    async def create_collection(
        self, *, user_id: uuid.UUID, name: str, description: str | None
    ) -> MemoryCollection:
        collection = MemoryCollection(user_id=user_id, name=name, description=description)
        self._session.add(collection)
        await self._session.flush()
        return collection

    async def list_collections(self, *, user_id: uuid.UUID) -> list[MemoryCollection]:
        result = await self._session.execute(
            select(MemoryCollection)
            .where(MemoryCollection.user_id == user_id)
            .order_by(MemoryCollection.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_collection(
        self, *, collection_id: uuid.UUID, user_id: uuid.UUID
    ) -> MemoryCollection | None:
        result = await self._session.execute(
            select(MemoryCollection).where(
                MemoryCollection.id == collection_id,
                MemoryCollection.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_to_collection(self, *, collection_id: uuid.UUID, memory_id: uuid.UUID) -> None:
        exists = (
            await self._session.execute(
                select(MemoryCollectionItem.id).where(
                    MemoryCollectionItem.collection_id == collection_id,
                    MemoryCollectionItem.memory_id == memory_id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            self._session.add(
                MemoryCollectionItem(collection_id=collection_id, memory_id=memory_id)
            )
            await self._session.flush()

    # ---- knowledge sources / search logs -------------------------------- #
    async def get_or_create_source(
        self,
        *,
        user_id: uuid.UUID,
        source_type: MemorySourceType,
        external_ref: str,
        title: str | None,
    ) -> tuple[KnowledgeSource, bool]:
        existing = (
            await self._session.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.user_id == user_id,
                    KnowledgeSource.source_type == source_type,
                    KnowledgeSource.external_ref == external_ref,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False
        source = KnowledgeSource(
            user_id=user_id,
            source_type=source_type,
            external_ref=external_ref,
            title=title,
        )
        self._session.add(source)
        await self._session.flush()
        return source, True

    async def log_search(
        self, *, user_id: uuid.UUID, query: str, result_count: int, latency_ms: int
    ) -> None:
        self._session.add(
            MemorySearchLog(
                user_id=user_id,
                query=query[:500],
                result_count=result_count,
                latency_ms=latency_ms,
            )
        )
        await self._session.flush()
