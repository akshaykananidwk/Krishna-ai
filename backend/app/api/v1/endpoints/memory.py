"""Memory Engine endpoints (Module 4). All routes require authentication."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, MemoryServiceDep
from app.models.memory import MemorySourceType, MemoryStatus
from app.schemas.common import Message
from app.schemas.memory import (
    CollectionCreate,
    CollectionPublic,
    FeedbackRequest,
    MemoryCreate,
    MemoryPublic,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryUpdate,
    SearchResult,
    TagRequest,
)

router = APIRouter(prefix="/memory", tags=["Memory Engine"])


@router.post(
    "",
    response_model=MemoryPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create (and auto-embed) a memory",
)
async def create_memory(
    payload: MemoryCreate,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.create_memory(user_id=user.id, payload=payload)
    return MemoryPublic.from_item(item)


@router.get("", response_model=list[MemoryPublic], summary="List memories")
async def list_memories(
    service: MemoryServiceDep,
    user: CurrentUser,
    source_type: MemorySourceType | None = None,
    pinned: bool | None = None,
    status_filter: MemoryStatus = Query(default=MemoryStatus.ACTIVE, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[MemoryPublic]:
    items = await service.list(
        user_id=user.id,
        status=status_filter,
        source_type=source_type,
        pinned=pinned,
        limit=limit,
        offset=offset,
    )
    return [MemoryPublic.from_item(i) for i in items]


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Semantic + filtered search over memories",
)
async def search_memories(
    request: MemorySearchRequest,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemorySearchResponse:
    ranked, latency = await service.search(user_id=user.id, request=request)
    return MemorySearchResponse(
        query=request.query,
        latency_ms=latency,
        results=[
            SearchResult(
                memory=MemoryPublic.from_item(r.item),
                score=round(r.score, 4),
                similarity=round(r.similarity, 4),
            )
            for r in ranked
        ],
    )


@router.get("/{memory_id}", response_model=MemoryPublic, summary="Get a memory")
async def get_memory(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.get(user_id=user.id, memory_id=memory_id)
    return MemoryPublic.from_item(item)


@router.get(
    "/{memory_id}/related",
    response_model=list[SearchResult],
    summary="Find memories related to this one",
)
async def related_memories(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
    top_k: int = Query(default=5, ge=1, le=20),
) -> list[SearchResult]:
    ranked = await service.related(user_id=user.id, memory_id=memory_id, top_k=top_k)
    return [
        SearchResult(
            memory=MemoryPublic.from_item(r.item),
            score=round(r.score, 4),
            similarity=round(r.similarity, 4),
        )
        for r in ranked
    ]


@router.patch("/{memory_id}", response_model=MemoryPublic, summary="Update a memory")
async def update_memory(
    memory_id: uuid.UUID,
    payload: MemoryUpdate,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.update(
        user_id=user.id,
        memory_id=memory_id,
        title=payload.title,
        content=payload.content,
        importance=payload.importance,
        pinned=payload.pinned,
        tags=payload.tags,
    )
    return MemoryPublic.from_item(item)


@router.delete("/{memory_id}", response_model=Message, summary="Soft-delete a memory")
async def delete_memory(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> Message:
    await service.set_status(user_id=user.id, memory_id=memory_id, status=MemoryStatus.DELETED)
    return Message(detail="Memory moved to trash.")


@router.post("/{memory_id}/restore", response_model=MemoryPublic, summary="Restore a memory")
async def restore_memory(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.set_status(
        user_id=user.id, memory_id=memory_id, status=MemoryStatus.ACTIVE
    )
    return MemoryPublic.from_item(item)


@router.post("/{memory_id}/archive", response_model=MemoryPublic, summary="Archive a memory")
async def archive_memory(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.set_status(
        user_id=user.id, memory_id=memory_id, status=MemoryStatus.ARCHIVED
    )
    return MemoryPublic.from_item(item)


@router.post("/{memory_id}/bookmark", response_model=Message, summary="Toggle bookmark")
async def bookmark_memory(
    memory_id: uuid.UUID,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> Message:
    added = await service.bookmark(user_id=user.id, memory_id=memory_id)
    return Message(detail="Bookmarked." if added else "Bookmark removed.")


@router.post("/{memory_id}/feedback", response_model=Message, summary="Submit relevance feedback")
async def feedback_memory(
    memory_id: uuid.UUID,
    payload: FeedbackRequest,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> Message:
    await service.feedback(user_id=user.id, memory_id=memory_id, signal=payload.signal)
    return Message(detail="Thanks for the feedback.")


@router.post("/{memory_id}/tags", response_model=MemoryPublic, summary="Add tags")
async def add_tags(
    memory_id: uuid.UUID,
    payload: TagRequest,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> MemoryPublic:
    item = await service.add_tags(user_id=user.id, memory_id=memory_id, tags=payload.tags)
    return MemoryPublic.from_item(item)


# ---- collections ---- #
@router.post(
    "/collections/new",
    response_model=CollectionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
async def create_collection(
    payload: CollectionCreate,
    service: MemoryServiceDep,
    user: CurrentUser,
) -> CollectionPublic:
    collection = await service._repo.create_collection(
        user_id=user.id, name=payload.name, description=payload.description
    )
    return CollectionPublic.model_validate(collection)


@router.get(
    "/collections/all",
    response_model=list[CollectionPublic],
    summary="List collections",
)
async def list_collections(
    service: MemoryServiceDep,
    user: CurrentUser,
) -> list[CollectionPublic]:
    collections = await service._repo.list_collections(user_id=user.id)
    return [CollectionPublic.model_validate(c) for c in collections]
