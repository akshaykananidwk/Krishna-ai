"""Google Gemini embedding provider (lazy import — SDK optional at runtime)."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.embeddings.base import EmbeddingError

_DEFAULT_MODEL = "text-embedding-004"
_DEFAULT_DIM = 768


class GeminiEmbeddingProvider:
    def __init__(self, *, api_key: str, model: str | None = None) -> None:
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY is required for the Gemini embedder.")
        self._api_key = api_key
        self._model = model or _DEFAULT_MODEL
        self._dim = _DEFAULT_DIM
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    def _ensure_client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - env-dependent
                raise EmbeddingError("The 'google-genai' package is not installed.") from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._ensure_client()
        try:
            # google-genai is sync; run it off the event loop.
            import anyio

            result = await anyio.to_thread.run_sync(
                lambda: client.models.embed_content(model=self._model, contents=list(texts))
            )
        except Exception as exc:  # pragma: no cover - network
            raise EmbeddingError(f"Gemini embedding failed: {exc}") from exc
        return [list(e.values) for e in result.embeddings]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]
