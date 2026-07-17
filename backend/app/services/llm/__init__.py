"""LLM provider abstraction.

The rest of the app depends on the :class:`LLMClient` protocol, never on a
concrete SDK. This keeps the provider swappable and lets the test suite inject a
deterministic fake with no network calls.
"""

from app.services.llm.base import ChatTurn, LLMClient, LLMError

__all__ = ["LLMClient", "ChatTurn", "LLMError"]
