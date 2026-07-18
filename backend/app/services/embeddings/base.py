"""Provider-agnostic embedding interface."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


class EmbeddingError(Exception):
    """Raised when an embedding provider fails or is misconfigured."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into fixed-dimension vectors."""

    @property
    def name(self) -> str:
        # pragma: no cover - protocol
        ...

    @property
    def model(self) -> str:
        # pragma: no cover - protocol
        ...

    @property
    def dim(self) -> int:
        # pragma: no cover - protocol
        ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text (order preserved)."""
        # pragma: no cover - protocol
        ...

    async def embed_one(self, text: str) -> list[float]:
        # pragma: no cover - protocol
        ...
