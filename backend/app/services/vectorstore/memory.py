"""In-process vector store with exact cosine similarity.

A real implementation used for development and the test suite. Not intended for
large corpora — production uses :class:`QdrantVectorStore`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

from app.services.vectorstore.base import (
    VectorHit,
    VectorRecord,
    VectorSearchFilters,
)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def ensure_ready(self, *, dim: int) -> None:
        return None

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        for record in records:
            self._records[record.id] = record

    async def delete(self, ids: Sequence[str]) -> None:
        for id_ in ids:
            self._records.pop(id_, None)

    async def search(
        self,
        *,
        vector: list[float],
        user_id: str,
        limit: int,
        filters: VectorSearchFilters | None = None,
    ) -> list[VectorHit]:
        filters = filters or VectorSearchFilters()
        hits: list[VectorHit] = []
        for record in self._records.values():
            payload = record.payload
            if payload.get("user_id") != user_id:
                continue
            if not self._matches(payload, filters):
                continue
            score = _cosine(vector, record.vector)
            hits.append(VectorHit(id=record.id, score=score, payload=payload))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    @staticmethod
    def _matches(payload: dict, f: VectorSearchFilters) -> bool:
        if f.statuses and payload.get("status", "active") not in f.statuses:
            return False
        if f.source_types and payload.get("source_type") not in f.source_types:
            return False
        if f.tags:
            item_tags = set(payload.get("tags") or [])
            if not set(f.tags).issubset(item_tags):
                return False
        created = _parse_dt(payload.get("created_at"))
        if f.created_after and (created is None or created < f.created_after):
            return False
        return not (f.created_before and (created is None or created > f.created_before))
