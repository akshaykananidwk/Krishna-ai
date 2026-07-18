"""Provider-agnostic vector store interface."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


class VectorStoreError(Exception):
    """Raised when the vector store is unavailable or misconfigured."""


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    payload: dict


@dataclass
class VectorSearchFilters:
    """Metadata filters applied to a similarity search."""

    source_types: Sequence[str] | None = None
    tags: Sequence[str] | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    statuses: Sequence[str] = field(default_factory=lambda: ["active"])


@runtime_checkable
class VectorStore(Protocol):
    async def ensure_ready(self, *, dim: int) -> None:
        # pragma: no cover - protocol
        ...

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        # pragma: no cover - protocol
        ...

    async def search(
        self,
        *,
        vector: list[float],
        user_id: str,
        limit: int,
        filters: VectorSearchFilters | None = None,
    ) -> list[VectorHit]:
        # pragma: no cover - protocol
        ...

    async def delete(self, ids: Sequence[str]) -> None:
        # pragma: no cover - protocol
        ...
