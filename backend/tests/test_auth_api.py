"""End-to-end API tests for the authentication module."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_success(client, valid_user_payload):
    resp = await client.post("/api/v1/auth/register", json=valid_user_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == valid_user_payload["email"]
    assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_conflicts(client, valid_user_payload):
    await client.post("/api/v1/auth/register", json=valid_user_payload)
    resp = await client.post("/api/v1/auth/register", json=valid_user_payload)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "email_already_registered"


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "alllowercase1"},
    )
    assert resp.status_code == 422  # validation error (missing uppercase)


@pytest.mark.asyncio
async def test_login_success(client, valid_user_payload):
    await client.post("/api/v1/auth/register", json=valid_user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": valid_user_payload["email"],
            "password": valid_user_payload["password"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client, valid_user_payload):
    await client.post("/api/v1/auth/register", json=valid_user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": valid_user_payload["email"], "password": "WrongPass1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Whatever1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client, valid_user_payload):
    reg = await client.post("/api/v1/auth/register", json=valid_user_payload)
    access = reg.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == valid_user_payload["email"]


@pytest.mark.asyncio
async def test_refresh_rotates_token(client, valid_user_payload):
    reg = await client.post("/api/v1/auth/register", json=valid_user_payload)
    old_refresh = reg.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # Old refresh token must now be revoked (rotation).
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, valid_user_payload):
    reg = await client.post("/api/v1/auth/register", json=valid_user_payload)
    refresh = reg.json()["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200

    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected(client):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
