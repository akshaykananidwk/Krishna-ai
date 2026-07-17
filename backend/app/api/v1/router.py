"""Aggregate router for API v1.

New modules register their routers here as the project grows.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router)
