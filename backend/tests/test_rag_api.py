"""End-to-end test for the RAG streaming endpoint."""

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
async def test_rag_query_streams_grounded_answer(client, auth_headers):
    # Seed a memory the retriever should surface.
    await client.post(
        "/api/v1/memory",
        json={
            "content": "The office wifi password is dolphin-sunrise-42",
            "title": "Wifi",
            "source_type": "note",
        },
        headers=auth_headers,
    )

    resp = await client.post(
        "/api/v1/rag/query",
        json={"query": "what is the office wifi password", "top_k": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types[0] == "sources"
    assert "delta" in types
    assert types[-1] == "done"

    # The seeded memory should have been retrieved as a source.
    sources = events[0]["sources"]
    assert any(s["title"] == "Wifi" for s in sources)

    done = events[-1]
    assert done["used_memories"] >= 1
    assert done["model"] == "fake-model"


@pytest.mark.asyncio
async def test_rag_query_requires_auth(client):
    resp = await client.post("/api/v1/rag/query", json={"query": "hi"})
    assert resp.status_code == 401
