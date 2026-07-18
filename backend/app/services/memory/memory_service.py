"""Memory Engine business logic: ingest, embed, search, rank, curate."""

from __future__ import annotations

import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.exceptions import ResourceNotFoundError
from app.models.memory import (
    EmbeddingStatus,
    MemoryItem,
    MemoryStatus,
)
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest
from app.services.embeddings.base import EmbeddingError, EmbeddingProvider
from app.services.memory.ranking import RankingSignals, compute_score
from app.services.vectorstore.base import (
    VectorRecord,
    VectorSearchFilters,
    VectorStore,
    VectorStoreError,
)

_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "have",
    "has",
    "was",
    "are",
    "you",
    "your",
    "but",
    "not",
    "all",
    "any",
    "can",
    "will",
    "would",
    "about",
    "into",
    "them",
    "they",
    "were",
    "what",
    "when",
    "which",
    "there",
    "their",
    "been",
    "than",
    "then",
    "some",
    "just",
    "like",
    "over",
    "also",
}
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]{3,}")


@dataclass
class RankedMemory:
    item: MemoryItem
    score: float
    similarity: float


def _auto_tags(text: str, *, limit: int = 5) -> list[str]:
    counts = Counter(w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


class MemoryService:
    def __init__(
        self,
        repo: MemoryRepository,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._repo = repo
        self._emb = embeddings
        self._vs = vector_store

    # ---- create / ingest ------------------------------------------------ #
    async def create_memory(self, *, user_id: uuid.UUID, payload: MemoryCreate) -> MemoryItem:
        item = await self._repo.create_item(
            user_id=user_id,
            content=payload.content,
            title=payload.title,
            source_type=payload.source_type,
            source_ref=payload.source_ref,
            importance=payload.importance,
            pinned=payload.pinned,
        )
        tags = payload.tags or _auto_tags(f"{payload.title or ''} {payload.content}")
        await self._repo.add_tags(
            memory_id=item.id, tags=tags, source="manual" if payload.tags else "auto"
        )
        for key, value in payload.metadata.items():
            await self._repo.set_metadata(
                memory_id=item.id, key=key[:64], value_encrypted=encrypt(value)
            )
        if payload.source_ref:
            await self._repo.get_or_create_source(
                user_id=user_id,
                source_type=payload.source_type,
                external_ref=payload.source_ref,
                title=payload.title,
            )
        await self._session_refresh(item)
        await self.embed_memory(item, tags=tags)
        return item

    async def _session_refresh(self, item: MemoryItem) -> None:
        # Ensure the tags relationship reflects freshly-added rows.
        await self._repo._session.refresh(item, attribute_names=["tags"])

    async def embed_memory(self, item: MemoryItem, *, tags: list[str] | None = None) -> None:
        """Embed a memory and store its vector. Records ready/failed status."""
        text = f"{item.title or ''}\n{item.content}".strip()
        if tags is not None:
            tag_list = tags
        else:
            # Load tags via an awaitable refresh so we never trigger a sync lazy
            # load in the async context (e.g. from the retry worker).
            await self._repo._session.refresh(item, attribute_names=["tags"])
            tag_list = [t.tag for t in item.tags]
        try:
            vector = await self._emb.embed_one(text)
            await self._vs.ensure_ready(dim=self._emb.dim)
            await self._detect_duplicate(item, vector)
            await self._vs.upsert(
                [
                    VectorRecord(
                        id=str(item.id),
                        vector=vector,
                        payload=self._payload(item, tag_list),
                    )
                ]
            )
            await self._repo.upsert_embedding(
                memory_id=item.id,
                provider=self._emb.name,
                model=self._emb.model,
                dim=self._emb.dim,
                vector_id=str(item.id),
                status=EmbeddingStatus.READY,
            )
        except (EmbeddingError, VectorStoreError) as exc:
            await self._repo.upsert_embedding(
                memory_id=item.id,
                provider=self._emb.name,
                model=self._emb.model,
                dim=self._emb.dim,
                vector_id=str(item.id),
                status=EmbeddingStatus.FAILED,
                error=str(exc)[:500],
            )

    async def _detect_duplicate(self, item: MemoryItem, vector: list[float]) -> None:
        hits = await self._vs.search(vector=vector, user_id=str(item.user_id), limit=1)
        if (
            hits
            and hits[0].id != str(item.id)
            and (hits[0].score >= settings.MEMORY_DUPLICATE_THRESHOLD)
        ):
            await self._repo.add_link(
                user_id=item.user_id,
                source_memory_id=item.id,
                target_memory_id=uuid.UUID(hits[0].id),
                link_type="duplicate",
                score=hits[0].score,
            )

    @staticmethod
    def _payload(item: MemoryItem, tags: list[str]) -> dict:
        return {
            "user_id": str(item.user_id),
            "source_type": item.source_type.value,
            "status": item.status.value,
            "tags": tags,
            "title": item.title,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    # ---- retrieval ------------------------------------------------------ #
    async def search(
        self, *, user_id: uuid.UUID, request: MemorySearchRequest
    ) -> tuple[list[RankedMemory], int]:
        started = time.perf_counter()
        qvec = await self._emb.embed_one(request.query)
        filters = VectorSearchFilters(
            source_types=[s.value for s in request.source_types] if request.source_types else None,
            tags=[t.lower() for t in request.tags] if request.tags else None,
            created_after=request.created_after,
            created_before=request.created_before,
        )
        hits = await self._vs.search(
            vector=qvec,
            user_id=str(user_id),
            limit=request.top_k * 3,  # over-fetch for reranking
            filters=filters,
        )
        hit_ids = [uuid.UUID(h.id) for h in hits]
        items = await self._repo.items_by_ids(ids=hit_ids, user_id=user_id)
        feedback = await self._repo.feedback_totals(memory_ids=list(items.keys()))

        ranked: list[RankedMemory] = []
        for hit in hits:
            item = items.get(uuid.UUID(hit.id))
            if item is None or item.status != MemoryStatus.ACTIVE:
                continue
            if hit.score < settings.RAG_MIN_SCORE:
                continue
            score = compute_score(
                RankingSignals(
                    similarity=hit.score,
                    created_at=item.created_at,
                    importance=item.importance,
                    access_count=item.access_count,
                    feedback=feedback.get(item.id, 0),
                    pinned=item.pinned,
                )
            )
            ranked.append(RankedMemory(item=item, score=score, similarity=hit.score))

        ranked.sort(key=lambda r: r.score, reverse=True)
        ranked = ranked[: request.top_k]

        await self._repo.touch_access([r.item for r in ranked])
        latency_ms = int((time.perf_counter() - started) * 1000)
        await self._repo.log_search(
            user_id=user_id,
            query=request.query,
            result_count=len(ranked),
            latency_ms=latency_ms,
        )
        return ranked, latency_ms

    async def related(
        self, *, user_id: uuid.UUID, memory_id: uuid.UUID, top_k: int = 5
    ) -> list[RankedMemory]:
        item = await self.get(user_id=user_id, memory_id=memory_id)
        request = MemorySearchRequest(
            query=f"{item.title or ''} {item.content}"[:500], top_k=top_k + 1
        )
        ranked, _ = await self.search(user_id=user_id, request=request)
        return [r for r in ranked if r.item.id != memory_id][:top_k]

    # ---- curation ------------------------------------------------------- #
    async def get(self, *, user_id: uuid.UUID, memory_id: uuid.UUID) -> MemoryItem:
        item = await self._repo.get_item(item_id=memory_id, user_id=user_id)
        if item is None:
            raise ResourceNotFoundError("Memory not found.")
        return item

    async def list(self, **kwargs) -> list[MemoryItem]:
        return await self._repo.list_items(**kwargs)

    async def update(
        self,
        *,
        user_id: uuid.UUID,
        memory_id: uuid.UUID,
        title: str | None,
        content: str | None,
        importance: float | None,
        pinned: bool | None,
        tags: list[str] | None,
    ) -> MemoryItem:
        item = await self.get(user_id=user_id, memory_id=memory_id)
        content_changed = content is not None and content != item.content
        if title is not None:
            item.title = title
        if content is not None:
            item.content = content
        if importance is not None:
            item.importance = importance
        if pinned is not None:
            item.pinned = pinned
        await self._repo._session.flush()
        if tags is not None:
            for existing in list(item.tags):
                await self._repo.remove_tag(memory_id=item.id, tag=existing.tag)
            await self._repo.add_tags(memory_id=item.id, tags=tags)
            await self._session_refresh(item)
        if content_changed or tags is not None:
            await self.embed_memory(item)
        return item

    async def set_status(
        self, *, user_id: uuid.UUID, memory_id: uuid.UUID, status: MemoryStatus
    ) -> MemoryItem:
        item = await self.get(user_id=user_id, memory_id=memory_id)
        await self._repo.set_status(item, status)
        # Keep the vector payload's status in sync (or drop on delete).
        if status == MemoryStatus.DELETED:
            await self._vs.delete([str(item.id)])
        else:
            await self.embed_memory(item)
        return item

    async def bookmark(self, *, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        await self.get(user_id=user_id, memory_id=memory_id)  # ownership check
        return await self._repo.toggle_bookmark(user_id=user_id, memory_id=memory_id)

    async def feedback(self, *, user_id: uuid.UUID, memory_id: uuid.UUID, signal: int) -> None:
        await self.get(user_id=user_id, memory_id=memory_id)
        await self._repo.set_feedback(
            user_id=user_id, memory_id=memory_id, signal=1 if signal >= 0 else -1
        )

    async def add_tags(
        self, *, user_id: uuid.UUID, memory_id: uuid.UUID, tags: list[str]
    ) -> MemoryItem:
        item = await self.get(user_id=user_id, memory_id=memory_id)
        await self._repo.add_tags(memory_id=item.id, tags=tags)
        await self._session_refresh(item)
        await self.embed_memory(item)
        return item
