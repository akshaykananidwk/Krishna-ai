"""Redis-backed fixed-window rate limiter middleware.

Keeps a per-client, per-minute counter in Redis. Fails open (allows the request)
if Redis is unreachable so that a cache outage never takes down the API.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.redis_client import redis_client
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self._limit = limit_per_minute or settings.RATE_LIMIT_PER_MINUTE

    async def dispatch(self, request: Request, call_next) -> Response:
        # Health/docs endpoints are never rate limited.
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "anonymous"
        key = f"ratelimit:{client_ip}:{request.url.path}"

        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, 60)
            if count > self._limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "rate_limited",
                        "detail": "Too many requests. Please slow down.",
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception:
            # Fail open: never let a Redis hiccup break the API.
            return await call_next(request)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self._limit - count))
        return response
