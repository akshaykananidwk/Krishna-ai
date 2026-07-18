"""Qdrant-backed vector store (production).

Lazy-imports ``qdrant-client`` so the app can run without it in local/test mode.
Vectors are stored with a payload that mirrors the metadata used for filtered
search; the point id is the ``memory_items.id``.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.config import settings
from app.services.vectorstore.base import (
    VectorHit,
    VectorRecord,
    VectorSearchFilters,
    VectorStoreError,
)


class QdrantVectorStore:
    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        collection: str | None = None,
    ) -> None:
        self._host = host or settings.QDRANT_HOST
        self._port = port or settings.QDRANT_PORT
        self._collection = collection or settings.QDRANT_COLLECTION
        self._client = None
        self._ready = False

    def _ensure_client(self):
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient
            except ImportError as exc:  # pragma: no cover - env-dependent
                raise VectorStoreError("The 'qdrant-client' package is not installed.") from exc
            self._client = AsyncQdrantClient(host=self._host, port=self._port)
        return self._client

    async def ensure_ready(self, *, dim: int) -> None:
        if self._ready:
            return
        client = self._ensure_client()
        from qdrant_client.models import Distance, VectorParams

        try:
            collections = await client.get_collections()
            names = {c.name for c in collections.collections}
            if self._collection not in names:
                await client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
        except Exception as exc:  # pragma: no cover - network
            raise VectorStoreError(f"Qdrant not reachable: {exc}") from exc
        self._ready = True

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        client = self._ensure_client()
        from qdrant_client.models import PointStruct

        points = [PointStruct(id=r.id, vector=r.vector, payload=r.payload) for r in records]
        await client.upsert(collection_name=self._collection, points=points)

    async def delete(self, ids: Sequence[str]) -> None:
        if not ids:
            return
        client = self._ensure_client()
        from qdrant_client.models import PointIdsList

        await client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=list(ids)),
        )

    async def search(
        self,
        *,
        vector: list[float],
        user_id: str,
        limit: int,
        filters: VectorSearchFilters | None = None,
    ) -> list[VectorHit]:
        client = self._ensure_client()
        from qdrant_client.models import (
            DatetimeRange,
            FieldCondition,
            Filter,
            MatchAny,
            MatchValue,
        )

        filters = filters or VectorSearchFilters()
        must = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        if filters.statuses:
            must.append(FieldCondition(key="status", match=MatchAny(any=list(filters.statuses))))
        if filters.source_types:
            must.append(
                FieldCondition(key="source_type", match=MatchAny(any=list(filters.source_types)))
            )
        if filters.tags:
            for tag in filters.tags:
                must.append(FieldCondition(key="tags", match=MatchValue(value=tag)))
        if filters.created_after or filters.created_before:
            must.append(
                FieldCondition(
                    key="created_at",
                    range=DatetimeRange(gte=filters.created_after, lte=filters.created_before),
                )
            )

        results = await client.search(
            collection_name=self._collection,
            query_vector=vector,
            query_filter=Filter(must=must),
            limit=limit,
        )
        return [VectorHit(id=str(r.id), score=r.score, payload=r.payload or {}) for r in results]
