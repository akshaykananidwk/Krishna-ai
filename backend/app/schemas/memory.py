"""Schemas for the Memory Engine (Module 4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.memory import MemorySourceType


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    title: str | None = Field(default=None, max_length=300)
    source_type: MemorySourceType = MemorySourceType.NOTE
    source_ref: str | None = Field(default=None, max_length=128)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    pinned: bool = False
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    pinned: bool | None = None
    tags: list[str] | None = None


class MemoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: MemorySourceType
    source_ref: str | None
    title: str | None
    content: str
    importance: float
    pinned: bool
    status: str
    access_count: int
    created_at: datetime
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_item(cls, item) -> MemoryPublic:
        return cls(
            id=item.id,
            source_type=item.source_type,
            source_ref=item.source_ref,
            title=item.title,
            content=item.content,
            importance=item.importance,
            pinned=item.pinned,
            status=item.status.value if hasattr(item.status, "value") else item.status,
            access_count=item.access_count,
            created_at=item.created_at,
            tags=[t.tag for t in item.tags],
        )


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=8, ge=1, le=50)
    source_types: list[MemorySourceType] | None = None
    tags: list[str] | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None


class SearchResult(BaseModel):
    memory: MemoryPublic
    score: float
    similarity: float


class MemorySearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    latency_ms: int


class TagRequest(BaseModel):
    tags: list[str] = Field(min_length=1)


class FeedbackRequest(BaseModel):
    signal: int = Field(description="+1 (helpful) or -1 (not helpful)")


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class CollectionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)
