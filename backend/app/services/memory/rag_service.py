"""Retrieval-Augmented Generation pipeline.

Flow: question → embed → vector search → rank → context build → prompt → LLM →
streamed response. Reuses the AI-Chat ``LLMClient`` (composition, not
modification).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.core.config import settings
from app.schemas.memory import MemorySearchRequest
from app.services.llm.base import ChatTurn, LLMClient, LLMError
from app.services.memory.context_builder import (
    RetrievedMemory,
    build_context,
    build_system_prompt,
)
from app.services.memory.memory_service import MemoryService


class RagService:
    def __init__(self, memory: MemoryService, llm: LLMClient) -> None:
        self._memory = memory
        self._llm = llm

    async def stream_answer(
        self, *, user_id: uuid.UUID, question: str, top_k: int
    ) -> AsyncIterator[dict]:
        """Yield SSE-style events: start, sources, delta, done, error."""
        ranked, _ = await self._memory.search(
            user_id=user_id,
            request=MemorySearchRequest(query=question, top_k=top_k),
        )
        retrieved = [
            RetrievedMemory(
                memory_id=str(r.item.id),
                title=r.item.title,
                content=r.item.content,
                source_type=r.item.source_type.value,
                score=r.score,
            )
            for r in ranked
        ]
        context, included = build_context(retrieved, max_chars=settings.RAG_MAX_CONTEXT_CHARS)
        system = build_system_prompt(settings.AI_SYSTEM_PROMPT, context)

        yield {
            "type": "sources",
            "sources": [
                {"index": i + 1, "memory_id": m.memory_id, "title": m.title}
                for i, m in enumerate(included)
            ],
        }

        parts: list[str] = []
        try:
            async for delta in self._llm.stream_reply(
                system=system,
                history=[ChatTurn(role="user", content=question)],
            ):
                parts.append(delta)
                yield {"type": "delta", "text": delta}
        except LLMError as exc:
            yield {"type": "error", "detail": str(exc)}
            return

        yield {
            "type": "done",
            "content": "".join(parts),
            "model": self._llm.model,
            "used_memories": len(included),
        }
