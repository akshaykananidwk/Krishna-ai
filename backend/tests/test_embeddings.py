"""Unit tests for the local embedding provider."""

from __future__ import annotations

import math

import pytest
from app.services.embeddings.factory import build_embedding_provider
from app.services.embeddings.local import LocalEmbeddingProvider


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


@pytest.mark.asyncio
async def test_dimension_and_determinism():
    p = LocalEmbeddingProvider(dim=128)
    v1 = await p.embed_one("the quick brown fox")
    v2 = await p.embed_one("the quick brown fox")
    assert len(v1) == 128
    assert v1 == v2  # deterministic


@pytest.mark.asyncio
async def test_unit_norm():
    p = LocalEmbeddingProvider(dim=64)
    v = await p.embed_one("hello world memory engine")
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_similar_text_scores_higher_than_unrelated():
    p = LocalEmbeddingProvider(dim=512)
    base = await p.embed_one("machine learning models and neural networks")
    similar = await p.embed_one("neural networks power machine learning")
    unrelated = await p.embed_one("i went hiking near the mountain river")
    assert _cosine(base, similar) > _cosine(base, unrelated)


@pytest.mark.asyncio
async def test_batch_matches_single():
    p = LocalEmbeddingProvider(dim=64)
    batch = await p.embed(["alpha beta", "gamma delta"])
    assert batch[0] == await p.embed_one("alpha beta")
    assert len(batch) == 2


def test_factory_builds_local():
    provider = build_embedding_provider("local")
    assert provider.name == "local"
