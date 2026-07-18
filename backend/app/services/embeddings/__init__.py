"""Embedding provider abstraction.

Providers are never hardcoded: the rest of the app depends on the
:class:`EmbeddingProvider` protocol and obtains a concrete instance from
:func:`build_embedding_provider`, chosen by configuration.
"""

from app.services.embeddings.base import EmbeddingError, EmbeddingProvider
from app.services.embeddings.factory import build_embedding_provider

__all__ = ["EmbeddingProvider", "EmbeddingError", "build_embedding_provider"]
