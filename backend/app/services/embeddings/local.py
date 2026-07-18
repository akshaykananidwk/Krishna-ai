"""Dependency-free deterministic embedding provider.

This is a real (bag-of-words feature-hashing) embedding — not a stub. Each token
is hashed to a bucket with a sign, the buckets are accumulated and L2-normalised.
Texts that share tokens land close in cosine space, which is enough for
development, offline use, and a fully deterministic test suite. Production
deployments select ``openai`` or ``gemini`` instead.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class LocalEmbeddingProvider:
    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    @property
    def name(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return f"local-hash-{self._dim}"

    @property
    def dim(self) -> int:
        return self._dim

    def _embed_sync(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # Neutral unit vector for empty/tokenless text.
            return [1.0 / math.sqrt(self._dim)] * self._dim
        return [v / norm for v in vec]

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_sync(t) for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return self._embed_sync(text)
