"""SQLAlchemy ORM models.

Importing the models here ensures they are registered on ``Base.metadata`` so
that Alembic autogeneration and ``create_all`` see every table.
"""

from app.models.base import Base
from app.models.chat import Conversation, Message, MessageRole
from app.models.memory import (
    EmbeddingStatus,
    KnowledgeSource,
    MemoryBookmark,
    MemoryCollection,
    MemoryCollectionItem,
    MemoryEmbedding,
    MemoryFeedback,
    MemoryItem,
    MemoryLink,
    MemoryMetadata,
    MemorySearchLog,
    MemorySourceType,
    MemoryStatus,
    MemoryTag,
)
from app.models.user import AuditLog, RefreshToken, User

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "AuditLog",
    "Conversation",
    "Message",
    "MessageRole",
    "MemoryItem",
    "MemoryEmbedding",
    "MemoryTag",
    "MemoryCollection",
    "MemoryCollectionItem",
    "MemoryBookmark",
    "MemoryFeedback",
    "MemoryLink",
    "MemoryMetadata",
    "MemorySearchLog",
    "KnowledgeSource",
    "MemorySourceType",
    "MemoryStatus",
    "EmbeddingStatus",
]
