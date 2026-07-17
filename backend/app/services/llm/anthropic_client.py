"""Anthropic-backed :class:`LLMClient` implementation."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from app.core.config import settings
from app.services.llm.base import ChatTurn, LLMError


class AnthropicLLMClient:
    """Streams replies from Claude via the official Anthropic SDK.

    The SDK is imported lazily so the app (and its test suite) can run without
    the ``anthropic`` package or an API key present.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.ANTHROPIC_API_KEY
        self._model = model or settings.ANTHROPIC_MODEL
        self._max_tokens = max_tokens or settings.AI_MAX_TOKENS
        self._client = None  # created on first use

    @property
    def model(self) -> str:
        return self._model

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise LLMError("AI chat is not configured. Set ANTHROPIC_API_KEY to enable it.")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError("The 'anthropic' package is not installed.") from exc
        self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def stream_reply(
        self,
        *,
        system: str,
        history: Sequence[ChatTurn],
    ) -> AsyncIterator[str]:
        client = self._ensure_client()
        messages = [{"role": turn.role, "content": turn.content} for turn in history]
        try:
            async with client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except LLMError:
            raise
        except Exception as exc:  # pragma: no cover - network/provider failures
            raise LLMError(f"LLM provider error: {exc}") from exc
