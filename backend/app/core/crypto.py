"""AES-256-GCM helpers for field-level encryption of sensitive data at rest.

Used for encrypting sensitive user-content columns (e.g. note bodies) before
they are persisted. The key is derived from ``settings.ENCRYPTION_KEY`` which
must be 64 hex characters (32 bytes).
"""

from __future__ import annotations

import base64
import os

from app.core.config import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_BYTES = 12


def _key() -> bytes:
    raw = bytes.fromhex(settings.ENCRYPTION_KEY)
    if len(raw) != 32:
        raise ValueError("ENCRYPTION_KEY must be 32 bytes (64 hex characters) for AES-256.")
    return raw


def encrypt(plaintext: str) -> str:
    """Encrypt ``plaintext`` and return a base64 ``nonce || ciphertext`` blob."""
    aesgcm = AESGCM(_key())
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(blob: str) -> str:
    """Reverse :func:`encrypt`."""
    raw = base64.b64decode(blob)
    nonce, ciphertext = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
    aesgcm = AESGCM(_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
