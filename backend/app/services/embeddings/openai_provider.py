"""OpenAI embedding provider (lazy import — SDK optional at runtime)."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.embeddings.base import EmbeddingError

_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}
_DEFAULT_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingProvider:
    def __init__(self, *, api_key: str, model: str | None = None) -> None:
        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for the OpenAI embedder.")
        self._api_key = api_key
        self._model = model or _DEFAULT_MODEL
        self._dim = _MODEL_DIMS.get(self._model, 1536)
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    def _ensure_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - env-dependent
                raise EmbeddingError("The 'openai' package is not installed.") from exc
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._ensure_client()
        try:
            resp = await client.embeddings.create(model=self._model, input=list(texts))
        except Exception as exc:  # pragma: no cover - network
            raise EmbeddingError(f"OpenAI embedding failed: {exc}") from exc
        return [item.embedding for item in resp.data]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]
