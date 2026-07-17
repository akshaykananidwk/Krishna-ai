"""Shared async Redis client used for caching, rate-limiting and token deny-lists."""

from __future__ import annotations

import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def close_redis() -> None:
    await redis_client.aclose()
