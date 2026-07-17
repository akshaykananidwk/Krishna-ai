"""AI Chat endpoints (Module: AI Chat / Conversation History).

Routes (all require authentication):
    POST   /chat/conversations                      create a conversation
    GET    /chat/conversations                      list the user's conversations
    GET    /chat/conversations/{id}                 conversation with messages
    PATCH  /chat/conversations/{id}                 rename a conversation
    DELETE /chat/conversations/{id}                 delete a conversation
    POST   /chat/conversations/{id}/messages        send a message; streams the
                                                    assistant reply as SSE
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.deps import ChatServiceDep, CurrentUser
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessagePublic,
    SendMessageRequest,
)
from app.schemas.common import Message

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post(
    "/conversations",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
)
async def create_conversation(
    payload: ConversationCreate,
    service: ChatServiceDep,
    user: CurrentUser,
) -> ConversationSummary:
    conversation = await service.create_conversation(user_id=user.id, title=payload.title)
    return ConversationSummary.model_validate(conversation)


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="List conversations",
)
async def list_conversations(
    service: ChatServiceDep,
    user: CurrentUser,
) -> list[ConversationSummary]:
    conversations = await service.list_conversations(user_id=user.id)
    return [ConversationSummary.model_validate(c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get a conversation with its messages",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    service: ChatServiceDep,
    user: CurrentUser,
) -> ConversationDetail:
    conversation = await service.get_conversation(user_id=user.id, conversation_id=conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessagePublic.model_validate(m) for m in conversation.messages],
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="Rename a conversation",
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    service: ChatServiceDep,
    user: CurrentUser,
) -> ConversationSummary:
    conversation = await service.rename_conversation(
        user_id=user.id, conversation_id=conversation_id, title=payload.title
    )
    return ConversationSummary.model_validate(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=Message,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    service: ChatServiceDep,
    user: CurrentUser,
) -> Message:
    await service.delete_conversation(user_id=user.id, conversation_id=conversation_id)
    return Message(detail="Conversation deleted.")


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Send a message and stream the assistant reply (SSE)",
    response_class=StreamingResponse,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    service: ChatServiceDep,
    user: CurrentUser,
) -> StreamingResponse:
    # Validate ownership/existence up front so a missing conversation returns a
    # real 404 instead of an error buried inside the event stream.
    await service.get_conversation(user_id=user.id, conversation_id=conversation_id)

    async def event_stream() -> AsyncIterator[bytes]:
        async for event in service.stream_reply_events(
            user_id=user.id,
            conversation_id=conversation_id,
            content=payload.content,
        ):
            yield f"data: {json.dumps(event)}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
