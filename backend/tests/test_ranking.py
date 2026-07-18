"""Unit tests for the memory ranking function."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.memory.ranking import (
    RankingSignals,
    compute_score,
    feedback_score,
    frequency_score,
    recency_score,
)

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def _signals(**kw):
    base = {
        "similarity": 0.5,
        "created_at": NOW,
        "importance": 0.5,
        "access_count": 0,
        "feedback": 0,
        "pinned": False,
    }
    base.update(kw)
    return RankingSignals(**base)


def test_recency_decays_with_age():
    recent = recency_score(NOW, now=NOW)
    old = recency_score(NOW - timedelta(days=60), now=NOW)
    assert recent > old
    assert 0.0 <= old <= recent <= 1.0


def test_frequency_monotonic_and_bounded():
    assert frequency_score(0) == 0.0
    assert frequency_score(5) > frequency_score(1)
    assert frequency_score(10_000) <= 1.0


def test_feedback_symmetry():
    assert feedback_score(3) > 0
    assert feedback_score(-3) < 0
    assert abs(feedback_score(0)) < 1e-9


def test_higher_similarity_ranks_higher():
    low = compute_score(_signals(similarity=0.2), now=NOW)
    high = compute_score(_signals(similarity=0.9), now=NOW)
    assert high > low


def test_pinned_boosts_score():
    plain = compute_score(_signals(pinned=False), now=NOW)
    pinned = compute_score(_signals(pinned=True), now=NOW)
    assert pinned > plain


def test_importance_and_feedback_contribute():
    baseline = compute_score(_signals(), now=NOW)
    important = compute_score(_signals(importance=1.0), now=NOW)
    upvoted = compute_score(_signals(feedback=5), now=NOW)
    downvoted = compute_score(_signals(feedback=-5), now=NOW)
    assert important > baseline
    assert upvoted > baseline > downvoted
