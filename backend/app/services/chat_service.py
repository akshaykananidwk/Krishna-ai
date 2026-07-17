"""AI Chat business logic (Module: AI Chat / Conversation History)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError
from app.models.chat import Conversation, MessageRole
from app.repositories.chat_repository import ChatRepository
from app.services.llm.base import ChatTurn, LLMClient, LLMError

_TITLE_MAX = 60


def _derive_title(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    return (cleaned[:_TITLE_MAX] + "…") if len(cleaned) > _TITLE_MAX else cleaned or "New chat"


class ChatService:
    """Conversation CRUD plus streamed assistant replies."""

    def __init__(self, repo: ChatRepository, llm: LLMClient) -> None:
        self._repo = repo
        self._llm = llm

    # ---- conversation management ---------------------------------------- #
    async def create_conversation(self, *, user_id: uuid.UUID, title: str | None) -> Conversation:
        return await self._repo.create_conversation(user_id=user_id, title=title)

    async def list_conversations(self, *, user_id: uuid.UUID) -> list[Conversation]:
        return await self._repo.list_conversations(user_id=user_id)

    async def get_conversation(
        self, *, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._repo.get_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        if conversation is None:
            raise ResourceNotFoundError("Conversation not found.")
        return conversation

    async def rename_conversation(
        self, *, user_id: uuid.UUID, conversation_id: uuid.UUID, title: str
    ) -> Conversation:
        conversation = await self.get_conversation(user_id=user_id, conversation_id=conversation_id)
        await self._repo.update_title(conversation, title)
        return conversation

    async def delete_conversation(self, *, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        conversation = await self.get_conversation(user_id=user_id, conversation_id=conversation_id)
        await self._repo.delete_conversation(conversation)

    # ---- streamed reply ------------------------------------------------- #
    async def stream_reply_events(
        self,
        *,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        content: str,
    ) -> AsyncIterator[dict]:
        """Persist the user message, stream the assistant reply, persist it.

        Yields structured events:
            {"type": "start", "conversation_id": ...}
            {"type": "delta", "text": "..."}
            {"type": "done",  "message_id": ..., "content": "...", "model": ...}
            {"type": "error", "detail": "..."}
        """
        conversation = await self.get_conversation(user_id=user_id, conversation_id=conversation_id)

        first_message = conversation.last_message_at is None
        await self._repo.add_message(
            conversation=conversation, role=MessageRole.USER, content=content
        )
        if first_message and conversation.title == "New chat":
            await self._repo.update_title(conversation, _derive_title(content))

        history = [
            ChatTurn(role=m.role.value, content=m.content)  # type: ignore[arg-type]
            for m in await self._repo.recent_messages(
                conversation_id=conversation.id, limit=settings.AI_HISTORY_LIMIT
            )
            if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
        ]

        yield {"type": "start", "conversation_id": str(conversation.id)}

        parts: list[str] = []
        try:
            async for delta in self._llm.stream_reply(
                system=settings.AI_SYSTEM_PROMPT, history=history
            ):
                parts.append(delta)
                yield {"type": "delta", "text": delta}
        except LLMError as exc:
            # Persist whatever was generated so the turn isn't silently lost.
            if parts:
                await self._persist_assistant("".join(parts), conversation)
            yield {"type": "error", "detail": str(exc)}
            return

        full = "".join(parts)
        message = await self._persist_assistant(full, conversation)
        yield {
            "type": "done",
            "message_id": str(message.id),
            "content": full,
            "model": self._llm.model,
        }

    async def _persist_assistant(self, text: str, conversation: Conversation):
        return await self._repo.add_message(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=text,
            model=self._llm.model,
        )
