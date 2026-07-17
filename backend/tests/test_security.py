"""Unit tests for the security primitives (no DB, no HTTP)."""

from __future__ import annotations

import time

import jwt
import pytest
from app.core.crypto import decrypt, encrypt
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("Dharma123")
    assert hashed != "Dharma123"
    assert verify_password("Dharma123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_verify_password_handles_malformed_hash():
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_roundtrip():
    token = create_access_token("user-123", extra_claims={"email": "a@b.c"})
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.c"
    assert payload["type"] == "access"


def test_token_type_mismatch_is_rejected():
    refresh = create_refresh_token("user-123")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(refresh, expected_type=TokenType.ACCESS)


def test_tokens_have_unique_jti():
    a = create_access_token("u")
    time.sleep(0.001)
    b = create_access_token("u")
    assert decode_token(a)["jti"] != decode_token(b)["jti"]


def test_aes_encrypt_decrypt_roundtrip():
    secret = "Bhagavad Gita, chapter 2, verse 47"
    blob = encrypt(secret)
    assert blob != secret
    assert decrypt(blob) == secret


def test_aes_ciphertext_is_nondeterministic():
    assert encrypt("same") != encrypt("same")
