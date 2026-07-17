"""Shared schemas used across modules."""

from __future__ import annotations

from pydantic import BaseModel


class Message(BaseModel):
    """Generic message envelope for simple success responses."""

    detail: str


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str
