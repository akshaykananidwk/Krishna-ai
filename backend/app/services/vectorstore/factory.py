"""Selects a vector store from configuration.

The in-memory store is a process-wide singleton so all requests in a running
app share the same index; tests override the dependency with a fresh instance.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.vectorstore.base import VectorStore, VectorStoreError
from app.services.vectorstore.memory import InMemoryVectorStore

_memory_singleton: InMemoryVectorStore | None = None


def build_vector_store(name: str | None = None) -> VectorStore:
    kind = (name or settings.VECTOR_STORE).lower()
    if kind == "memory":
        global _memory_singleton
        if _memory_singleton is None:
            _memory_singleton = InMemoryVectorStore()
        return _memory_singleton
    if kind == "qdrant":
        from app.services.vectorstore.qdrant_store import QdrantVectorStore

        return QdrantVectorStore()
    raise VectorStoreError(f"Unknown vector store: {kind!r}")
