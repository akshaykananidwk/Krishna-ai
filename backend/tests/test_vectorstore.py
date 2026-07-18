"""Tests for the in-memory vector store (cosine search + filters + isolation)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.services.vectorstore.base import VectorRecord, VectorSearchFilters
from app.services.vectorstore.memory import InMemoryVectorStore


def _payload(user="u1", source="note", tags=None, status="active", created=None):
    return {
        "user_id": user,
        "source_type": source,
        "tags": tags or [],
        "status": status,
        "created_at": (created or datetime(2026, 1, 1, tzinfo=UTC)).isoformat(),
    }


@pytest.mark.asyncio
async def test_search_orders_by_cosine():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord("a", [1.0, 0.0], _payload()),
            VectorRecord("b", [0.0, 1.0], _payload()),
        ]
    )
    hits = await store.search(vector=[1.0, 0.0], user_id="u1", limit=2)
    assert hits[0].id == "a"
    assert hits[0].score > hits[1].score


@pytest.mark.asyncio
async def test_user_isolation():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord("a", [1.0, 0.0], _payload(user="u1")),
            VectorRecord("b", [1.0, 0.0], _payload(user="u2")),
        ]
    )
    hits = await store.search(vector=[1.0, 0.0], user_id="u1", limit=10)
    assert [h.id for h in hits] == ["a"]


@pytest.mark.asyncio
async def test_tag_and_type_filters():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord("a", [1.0, 0.0], _payload(tags=["work"], source="note")),
            VectorRecord("b", [1.0, 0.0], _payload(tags=["home"], source="task")),
        ]
    )
    hits = await store.search(
        vector=[1.0, 0.0],
        user_id="u1",
        limit=10,
        filters=VectorSearchFilters(tags=["work"]),
    )
    assert [h.id for h in hits] == ["a"]

    hits = await store.search(
        vector=[1.0, 0.0],
        user_id="u1",
        limit=10,
        filters=VectorSearchFilters(source_types=["task"]),
    )
    assert [h.id for h in hits] == ["b"]


@pytest.mark.asyncio
async def test_time_filter_and_delete():
    store = InMemoryVectorStore()
    old = datetime(2020, 1, 1, tzinfo=UTC)
    new = datetime(2026, 6, 1, tzinfo=UTC)
    await store.upsert(
        [
            VectorRecord("old", [1.0, 0.0], _payload(created=old)),
            VectorRecord("new", [1.0, 0.0], _payload(created=new)),
        ]
    )
    hits = await store.search(
        vector=[1.0, 0.0],
        user_id="u1",
        limit=10,
        filters=VectorSearchFilters(created_after=datetime(2025, 1, 1, tzinfo=UTC)),
    )
    assert [h.id for h in hits] == ["new"]

    await store.delete(["new"])
    hits = await store.search(vector=[1.0, 0.0], user_id="u1", limit=10)
    assert [h.id for h in hits] == ["old"]


@pytest.mark.asyncio
async def test_status_filter_excludes_archived():
    store = InMemoryVectorStore()
    await store.upsert([VectorRecord("a", [1.0, 0.0], _payload(status="archived"))])
    hits = await store.search(vector=[1.0, 0.0], user_id="u1", limit=10)
    assert hits == []
