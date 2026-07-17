"""Persistence for conversations and messages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message, MessageRole


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(self, *, user_id: uuid.UUID, title: str | None) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title or "New chat")
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_conversation(
        self, *, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_conversations(self, *, user_id: uuid.UUID) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.archived_at.is_(None),
            )
            .order_by(
                Conversation.last_message_at.desc().nullslast(),
                Conversation.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def update_title(self, conversation: Conversation, title: str) -> None:
        conversation.title = title
        await self._session.flush()
        # ``updated_at`` is refreshed by the DB (onupdate); reload it within the
        # async context so later attribute access doesn't trigger lazy IO.
        await self._session.refresh(conversation)

    async def delete_conversation(self, conversation: Conversation) -> None:
        await self._session.delete(conversation)
        await self._session.flush()

    async def add_message(
        self,
        *,
        conversation: Conversation,
        role: MessageRole,
        content: str,
        model: str | None = None,
        token_count: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            model=model,
            token_count=token_count,
        )
        self._session.add(message)
        conversation.last_message_at = datetime.now(UTC)
        await self._session.flush()
        return message

    async def recent_messages(self, *, conversation_id: uuid.UUID, limit: int) -> list[Message]:
        """Return the most recent ``limit`` messages in chronological order."""
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
