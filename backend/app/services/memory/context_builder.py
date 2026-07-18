"""Builds a token-bounded context block from retrieved memories for RAG.

Prioritises the highest-ranked memories and stops once the character budget
(a proxy for tokens) is exhausted, so prompt size stays bounded regardless of
how much was retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedMemory:
    memory_id: str
    title: str | None
    content: str
    source_type: str
    score: float


def build_context(
    memories: list[RetrievedMemory],
    *,
    max_chars: int,
) -> tuple[str, list[RetrievedMemory]]:
    """Return (context_text, memories_actually_included)."""
    lines: list[str] = []
    used = 0
    included: list[RetrievedMemory] = []
    for i, mem in enumerate(memories, start=1):
        header = f"[{i}] ({mem.source_type}) {mem.title or 'Memory'}"
        body = mem.content.strip()
        block = f"{header}\n{body}"
        if used + len(block) > max_chars and included:
            break
        # Always include at least one, truncating if a single memory is huge.
        if len(block) > max_chars:
            block = block[: max_chars - 1] + "…"
        lines.append(block)
        used += len(block)
        included.append(mem)
    return "\n\n".join(lines), included


def build_system_prompt(base_prompt: str, context: str) -> str:
    if not context:
        return base_prompt
    return (
        f"{base_prompt}\n\n"
        "Use the following retrieved memories from the user's personal knowledge "
        "base to ground your answer. Cite them inline as [1], [2], … when you "
        "rely on them. If the memories don't contain the answer, say so and "
        "answer from general knowledge.\n\n"
        "=== RETRIEVED MEMORIES ===\n"
        f"{context}\n"
        "=== END MEMORIES ==="
    )
