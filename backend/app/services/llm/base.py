"""Provider-agnostic LLM interface."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatTurn:
    """A single prior turn passed to the model as context."""

    role: Role
    content: str


class LLMError(Exception):
    """Raised when the upstream LLM provider fails or is not configured."""


@runtime_checkable
class LLMClient(Protocol):
    """Streams an assistant reply for a conversation.

    Implementations yield text deltas as they arrive so the caller can forward
    them to the client in real time (Server-Sent Events).
    """

    async def stream_reply(
        self,
        *,
        system: str,
        history: Sequence[ChatTurn],
    ) -> AsyncIterator[str]:
        # pragma: no cover - protocol definition
        ...

    @property
    def model(self) -> str:
        # pragma: no cover - protocol definition
        ...
