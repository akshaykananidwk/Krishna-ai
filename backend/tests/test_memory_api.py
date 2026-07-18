"""End-to-end tests for the Memory Engine API (local embedder + in-memory store)."""

from __future__ import annotations

import pytest

ROCKET = {
    "content": "Project Apollo launch checklist and rocket engine specifications",
    "title": "Apollo notes",
    "source_type": "note",
    "tags": ["space", "apollo"],
}
GROCERY = {
    "content": "grocery shopping list bananas milk bread eggs",
    "source_type": "note",
}


async def _create(client, headers, body):
    resp = await client.post("/api/v1/memory", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_memory_with_tags(client, auth_headers):
    mem = await _create(client, auth_headers, ROCKET)
    assert mem["content"] == ROCKET["content"]
    assert set(mem["tags"]) == {"space", "apollo"}
    assert mem["status"] == "active"


@pytest.mark.asyncio
async def test_auto_tagging_when_no_tags_given(client, auth_headers):
    mem = await _create(client, auth_headers, GROCERY)
    assert len(mem["tags"]) > 0  # derived from content


@pytest.mark.asyncio
async def test_semantic_search_finds_relevant_memory(client, auth_headers):
    await _create(client, auth_headers, ROCKET)
    await _create(client, auth_headers, GROCERY)

    resp = await client.post(
        "/api/v1/memory/search",
        json={"query": "rocket engine specifications for Apollo", "top_k": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"], "expected at least one hit"
    top = body["results"][0]["memory"]
    assert "Apollo" in (top["title"] or "")
    assert body["results"][0]["similarity"] >= body["results"][-1]["similarity"]


@pytest.mark.asyncio
async def test_search_is_user_isolated(client, auth_headers):
    await _create(client, auth_headers, ROCKET)

    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "nakula@example.com", "password": "Dharma123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/memory/search",
        json={"query": "rocket engine Apollo", "top_k": 5},
        headers=other_headers,
    )
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_soft_delete_hides_then_restore_brings_back(client, auth_headers):
    mem = await _create(client, auth_headers, ROCKET)
    mid = mem["id"]

    deleted = await client.delete(f"/api/v1/memory/{mid}", headers=auth_headers)
    assert deleted.status_code == 200

    # Excluded from active list and from search.
    listing = await client.get("/api/v1/memory", headers=auth_headers)
    assert all(m["id"] != mid for m in listing.json())
    search = await client.post(
        "/api/v1/memory/search",
        json={"query": "rocket engine Apollo"},
        headers=auth_headers,
    )
    assert all(r["memory"]["id"] != mid for r in search.json()["results"])

    restored = await client.post(f"/api/v1/memory/{mid}/restore", headers=auth_headers)
    assert restored.status_code == 200
    search2 = await client.post(
        "/api/v1/memory/search",
        json={"query": "rocket engine Apollo"},
        headers=auth_headers,
    )
    assert any(r["memory"]["id"] == mid for r in search2.json()["results"])


@pytest.mark.asyncio
async def test_bookmark_feedback_and_tags(client, auth_headers):
    mem = await _create(client, auth_headers, ROCKET)
    mid = mem["id"]

    b1 = await client.post(f"/api/v1/memory/{mid}/bookmark", headers=auth_headers)
    assert "Bookmarked" in b1.json()["detail"]
    b2 = await client.post(f"/api/v1/memory/{mid}/bookmark", headers=auth_headers)
    assert "removed" in b2.json()["detail"]

    fb = await client.post(
        f"/api/v1/memory/{mid}/feedback", json={"signal": 1}, headers=auth_headers
    )
    assert fb.status_code == 200

    tagged = await client.post(
        f"/api/v1/memory/{mid}/tags", json={"tags": ["mission"]}, headers=auth_headers
    )
    assert "mission" in tagged.json()["tags"]


@pytest.mark.asyncio
async def test_update_and_pin(client, auth_headers):
    mem = await _create(client, auth_headers, ROCKET)
    mid = mem["id"]
    updated = await client.patch(
        f"/api/v1/memory/{mid}",
        json={"pinned": True, "importance": 0.9},
        headers=auth_headers,
    )
    assert updated.json()["pinned"] is True
    assert updated.json()["importance"] == 0.9


@pytest.mark.asyncio
async def test_related_memories(client, auth_headers):
    a = await _create(client, auth_headers, ROCKET)
    await _create(
        client,
        auth_headers,
        {
            "content": "Apollo rocket engine thrust and fuel notes",
            "source_type": "note",
        },
    )
    resp = await client.get(f"/api/v1/memory/{a['id']}/related", headers=auth_headers)
    assert resp.status_code == 200
    assert all(r["memory"]["id"] != a["id"] for r in resp.json())


@pytest.mark.asyncio
async def test_collections(client, auth_headers):
    created = await client.post(
        "/api/v1/memory/collections/new",
        json={"name": "Space", "description": "space stuff"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    listing = await client.get("/api/v1/memory/collections/all", headers=auth_headers)
    assert any(c["name"] == "Space" for c in listing.json())


@pytest.mark.asyncio
async def test_memory_requires_auth(client):
    resp = await client.get("/api/v1/memory")
    assert resp.status_code == 401
