"""RAG endpoint (Module 4): memory-grounded, streamed answers.

This is the memory-aware assistant. It retrieves the user's relevant memories,
builds a bounded context, and streams a grounded answer — without modifying the
existing AI-Chat module (it composes the shared LLMClient).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, RagServiceDep
from app.schemas.memory import RagQueryRequest

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/query",
    summary="Ask a question grounded in your memories (SSE stream)",
    response_class=StreamingResponse,
)
async def rag_query(
    payload: RagQueryRequest,
    service: RagServiceDep,
    user: CurrentUser,
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[bytes]:
        async for event in service.stream_answer(
            user_id=user.id, question=payload.query, top_k=payload.top_k
        ):
            yield f"data: {json.dumps(event)}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
