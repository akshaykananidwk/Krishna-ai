"""Aggregate router for API v1.

New modules register their routers here as the project grows.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, memory, rag

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(memory.router)
api_router.include_router(rag.router)
