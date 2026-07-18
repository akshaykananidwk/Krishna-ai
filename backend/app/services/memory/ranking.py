"""Memory ranking.

Combines vector similarity with recency, importance, access frequency, user
feedback, and a pinned boost into a single score. Pure functions — no IO — so
the weighting is unit-testable in isolation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

# Weights sum is informational; scores are relative, not probabilities.
W_SIMILARITY = 0.55
W_RECENCY = 0.15
W_IMPORTANCE = 0.15
W_FREQUENCY = 0.05
W_FEEDBACK = 0.10
PINNED_BOOST = 0.15

# Recency half-life in days (older memories decay toward 0).
_RECENCY_TAU_DAYS = 30.0


@dataclass
class RankingSignals:
    similarity: float  # cosine, roughly [-1, 1] → clamped to [0, 1]
    created_at: datetime
    importance: float  # [0, 1]
    access_count: int
    feedback: int  # summed +1 / -1 signals
    pinned: bool


def recency_score(created_at: datetime, *, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    return math.exp(-age_days / _RECENCY_TAU_DAYS)


def frequency_score(access_count: int) -> float:
    # Diminishing returns; saturates well before pathological counts.
    return min(1.0, math.log1p(max(0, access_count)) / math.log(50))


def feedback_score(feedback: int) -> float:
    # Squash the summed signal into [-1, 1] via tanh.
    return math.tanh(feedback / 3.0)


def compute_score(signals: RankingSignals, *, now: datetime | None = None) -> float:
    similarity = max(0.0, min(1.0, signals.similarity))
    score = (
        W_SIMILARITY * similarity
        + W_RECENCY * recency_score(signals.created_at, now=now)
        + W_IMPORTANCE * max(0.0, min(1.0, signals.importance))
        + W_FREQUENCY * frequency_score(signals.access_count)
        + W_FEEDBACK * feedback_score(signals.feedback)
    )
    if signals.pinned:
        score += PINNED_BOOST
    return score
