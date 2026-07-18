"""Personal Memory Engine models (Module 4).

PostgreSQL is the source of truth; Qdrant holds only vectors keyed back to
``memory_items.id``. Every table is scoped to a user for isolation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.types import GUID


class MemorySourceType(str, enum.Enum):
    CONVERSATION = "conversation"
    MEETING = "meeting"
    TASK = "task"
    REMINDER = "reminder"
    JOURNAL = "journal"
    DOCUMENT = "document"
    PDF = "pdf"
    OCR = "ocr"
    VOICE = "voice"
    IMAGE = "image"
    NOTE = "note"
    CUSTOM = "custom"


class MemoryStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"  # soft delete; purged by the cleanup worker


class EmbeddingStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


def _enum(py_enum, name: str):
    return SAEnum(py_enum, name=name, native_enum=False, length=32)


class MemoryItem(Base, UUIDMixin, TimestampMixin):
    """A single unit of remembered knowledge (the source of truth)."""

    __tablename__ = "memory_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[MemorySourceType] = mapped_column(
        _enum(MemorySourceType, "memory_source_type"), nullable=False
    )
    # Optional reference back to the origin row (e.g. a conversation id).
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)

    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[MemoryStatus] = mapped_column(
        _enum(MemoryStatus, "memory_status"),
        default=MemoryStatus.ACTIVE,
        nullable=False,
    )

    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    embedding: Mapped[MemoryEmbedding | None] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    tags: Mapped[list[MemoryTag]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_memory_items_user_status", "user_id", "status"),
        Index("ix_memory_items_user_type", "user_id", "source_type"),
    )


class MemoryEmbedding(Base, UUIDMixin, TimestampMixin):
    """Tracks the embedding of a memory item and its location in the vector store."""

    __tablename__ = "memory_embeddings"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("memory_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    # Point id inside the vector store (defaults to the memory id).
    vector_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EmbeddingStatus] = mapped_column(
        _enum(EmbeddingStatus, "embedding_status"),
        default=EmbeddingStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    memory: Mapped[MemoryItem] = relationship(back_populates="embedding")


class MemoryTag(Base, UUIDMixin):
    """A tag attached to a memory (manual or auto-generated)."""

    __tablename__ = "memory_tags"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped[MemoryItem] = relationship(back_populates="tags")

    __table_args__ = (UniqueConstraint("memory_id", "tag", name="uq_memory_tag"),)


class MemoryCollection(Base, UUIDMixin, TimestampMixin):
    """A user-defined grouping of memories."""

    __tablename__ = "memory_collections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collection_name"),)


class MemoryCollectionItem(Base, UUIDMixin):
    """Join between collections and memories."""

    __tablename__ = "memory_collection_items"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_collections.id", ondelete="CASCADE"), nullable=False
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("collection_id", "memory_id", name="uq_collection_item"),)


class MemoryBookmark(Base, UUIDMixin):
    """A user bookmark on a memory."""

    __tablename__ = "memory_bookmarks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "memory_id", name="uq_bookmark"),)


class MemoryFeedback(Base, UUIDMixin):
    """Relevance feedback used by the ranking function (``+1`` / ``-1``)."""

    __tablename__ = "memory_feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False
    )
    signal: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "memory_id", name="uq_feedback"),)


class MemoryLink(Base, UUIDMixin):
    """A relationship between two memories (related / duplicate / merged)."""

    __tablename__ = "memory_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False
    )
    target_memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(24), nullable=False)  # related|duplicate
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemoryMetadata(Base, UUIDMixin):
    """Arbitrary encrypted key/value metadata attached to a memory."""

    __tablename__ = "memory_metadata"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    # AES-256-GCM ciphertext (see app.core.crypto).
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("memory_id", "key", name="uq_metadata_key"),)


class MemorySearchLog(Base, UUIDMixin):
    """Audit + analytics record for each search (also feeds frequency ranking)."""

    __tablename__ = "memory_search_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeSource(Base, UUIDMixin, TimestampMixin):
    """A distinct ingestion origin, used to de-duplicate imports per user."""

    __tablename__ = "knowledge_sources"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[MemorySourceType] = mapped_column(
        _enum(MemorySourceType, "knowledge_source_type"), nullable=False
    )
    external_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "external_ref", name="uq_source_ref"),
    )
