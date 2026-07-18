"""Selects an embedding provider from configuration."""

from __future__ import annotations

from app.core.config import settings
from app.services.embeddings.base import EmbeddingError, EmbeddingProvider
from app.services.embeddings.local import LocalEmbeddingProvider


def build_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    provider = (name or settings.EMBEDDING_PROVIDER).lower()
    model = settings.EMBEDDING_MODEL or None

    if provider == "local":
        return LocalEmbeddingProvider(dim=settings.LOCAL_EMBEDDING_DIM)
    if provider == "openai":
        from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY, model=model)
    if provider == "gemini":
        from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY, model=model)

    raise EmbeddingError(f"Unknown embedding provider: {provider!r}")
