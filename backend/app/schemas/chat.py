"""Schemas for the AI Chat module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageRole


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    model: str | None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Lightweight representation for list views (no message bodies)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessagePublic]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
