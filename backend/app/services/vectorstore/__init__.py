"""Vector store abstraction (Qdrant in prod, in-memory for dev/tests)."""

from app.services.vectorstore.base import (
    VectorHit,
    VectorRecord,
    VectorSearchFilters,
    VectorStore,
    VectorStoreError,
)
from app.services.vectorstore.factory import build_vector_store

__all__ = [
    "VectorStore",
    "VectorRecord",
    "VectorHit",
    "VectorSearchFilters",
    "VectorStoreError",
    "build_vector_store",
]
