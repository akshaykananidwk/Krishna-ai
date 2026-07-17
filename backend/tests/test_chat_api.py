"""End-to-end tests for the AI Chat module (streaming mocked via FakeLLMClient)."""

from __future__ import annotations

import json

import pytest


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        line = block.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:") :].strip()))
    return events


@pytest.mark.asyncio
async def test_create_and_list_conversations(client, auth_headers):
    create = await client.post(
        "/api/v1/chat/conversations", json={"title": "Trip planning"}, headers=auth_headers
    )
    assert create.status_code == 201
    assert create.json()["title"] == "Trip planning"

    listing = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_conversations_require_auth(client):
    resp = await client.get("/api/v1/chat/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_send_message_streams_and_persists(client, auth_headers):
    conv = (await client.post("/api/v1/chat/conversations", json={}, headers=auth_headers)).json()

    resp = await client.post(
        f"/api/v1/chat/conversations/{conv['id']}/messages",
        json={"content": "Hi there, who are you?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "delta" in types
    assert types[-1] == "done"

    streamed = "".join(e["text"] for e in events if e["type"] == "delta")
    done = events[-1]
    assert done["content"] == streamed
    assert done["model"] == "fake-model"

    # The conversation now has the user + assistant messages persisted, and the
    # title was auto-derived from the first user message.
    detail = (
        await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=auth_headers)
    ).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert detail["messages"][1]["content"] == streamed
    assert detail["title"].startswith("Hi there")


@pytest.mark.asyncio
async def test_send_message_to_missing_conversation_404(client, auth_headers):
    resp = await client.post(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={"content": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_another_users_conversation(client, auth_headers):
    conv = (await client.post("/api/v1/chat/conversations", json={}, headers=auth_headers)).json()

    # Second user
    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "bhima@example.com", "password": "Dharma123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    resp = await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rename_and_delete_conversation(client, auth_headers):
    conv = (await client.post("/api/v1/chat/conversations", json={}, headers=auth_headers)).json()

    renamed = await client.patch(
        f"/api/v1/chat/conversations/{conv['id']}",
        json={"title": "Renamed"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    deleted = await client.delete(f"/api/v1/chat/conversations/{conv['id']}", headers=auth_headers)
    assert deleted.status_code == 200

    gone = await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=auth_headers)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_multi_turn_history_is_persisted(client, auth_headers):
    conv = (await client.post("/api/v1/chat/conversations", json={}, headers=auth_headers)).json()
    for text in ("first question", "second question"):
        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": text},
            headers=auth_headers,
        )
    detail = (
        await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=auth_headers)
    ).json()
    # 2 user + 2 assistant messages.
    assert len(detail["messages"]) == 4
