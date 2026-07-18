"""Memory Engine — vector-searchable personal knowledge (Module 4).

Revision ID: 0003_memory
Revises: 0002_chat
Create Date: 2026-07-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_memory"
down_revision: Union[str, None] = "0002_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _ts(col: str = "created_at"):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "memory_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memory_items_user_id", "memory_items", ["user_id"])
    op.create_index("ix_memory_items_user_status", "memory_items", ["user_id", "status"])
    op.create_index("ix_memory_items_user_type", "memory_items", ["user_id", "source_type"])

    op.create_table(
        "memory_embeddings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("memory_id", UUID, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("memory_id", name="uq_embedding_memory"),
    )

    op.create_table(
        "memory_tags",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("memory_id", UUID, nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("memory_id", "tag", name="uq_memory_tag"),
    )
    op.create_index("ix_memory_tags_memory_id", "memory_tags", ["memory_id"])
    op.create_index("ix_memory_tags_tag", "memory_tags", ["tag"])

    op.create_table(
        "memory_collections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_collection_name"),
    )
    op.create_index("ix_memory_collections_user_id", "memory_collections", ["user_id"])

    op.create_table(
        "memory_collection_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("collection_id", UUID, nullable=False),
        sa.Column("memory_id", UUID, nullable=False),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["collection_id"], ["memory_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("collection_id", "memory_id", name="uq_collection_item"),
    )

    op.create_table(
        "memory_bookmarks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("memory_id", UUID, nullable=False),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "memory_id", name="uq_bookmark"),
    )
    op.create_index("ix_memory_bookmarks_user_id", "memory_bookmarks", ["user_id"])

    op.create_table(
        "memory_feedback",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("memory_id", UUID, nullable=False),
        sa.Column("signal", sa.Integer(), nullable=False),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "memory_id", name="uq_feedback"),
    )
    op.create_index("ix_memory_feedback_user_id", "memory_feedback", ["user_id"])

    op.create_table(
        "memory_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source_memory_id", UUID, nullable=False),
        sa.Column("target_memory_id", UUID, nullable=False),
        sa.Column("link_type", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_memory_id"], ["memory_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memory_links_user_id", "memory_links", ["user_id"])

    op.create_table(
        "memory_metadata",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("memory_id", UUID, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("memory_id", "key", name="uq_metadata_key"),
    )
    op.create_index("ix_memory_metadata_memory_id", "memory_metadata", ["memory_id"])

    op.create_table(
        "memory_search_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memory_search_logs_user_id", "memory_search_logs", ["user_id"])

    op.create_table(
        "knowledge_sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("external_ref", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "source_type", "external_ref", name="uq_source_ref"),
    )
    op.create_index("ix_knowledge_sources_user_id", "knowledge_sources", ["user_id"])


def downgrade() -> None:
    for table in (
        "knowledge_sources",
        "memory_search_logs",
        "memory_metadata",
        "memory_links",
        "memory_feedback",
        "memory_bookmarks",
        "memory_collection_items",
        "memory_collections",
        "memory_tags",
        "memory_embeddings",
        "memory_items",
    ):
        op.drop_table(table)
