"""Shared pytest fixtures.

The suite runs against an in-memory SQLite database so it needs no external
services. Portable column types (:mod:`app.models.types`) make this possible.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

# Ensure a valid 32-byte encryption key before app settings load.
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
import pytest_asyncio
from app.api.deps import get_db
from app.core import redis_client as redis_module
from app.main import app
from app.models import Base
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


class _FakeRedis:
    """Minimal in-memory stand-in so rate-limit middleware works without Redis."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fake_redis = _FakeRedis()
    monkeypatch.setattr(redis_module, "redis_client", fake_redis)
    # The rate-limit middleware imported the client by reference at import time.
    from app.core import rate_limit as rl_module

    monkeypatch.setattr(rl_module, "redis_client", fake_redis)

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def valid_user_payload() -> dict[str, str]:
    return {
        "email": "arjuna@example.com",
        "password": "Dharma123",
        "full_name": "Arjuna Pandava",
    }
