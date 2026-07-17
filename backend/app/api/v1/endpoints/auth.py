"""Authentication endpoints (Module 1).

Routes:
    POST /auth/register  — create an account, returns tokens + user
    POST /auth/login     — email/password login
    POST /auth/refresh   — rotate a refresh token for a new pair
    POST /auth/logout    — revoke a refresh token
    GET  /auth/me        — current authenticated user
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentUser, RequestMeta
from app.schemas.common import Message
from app.schemas.token import AuthResponse, LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserLogin, UserPublic, UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    payload: UserRegister,
    service: AuthServiceDep,
    meta: RequestMeta,
) -> AuthResponse:
    return await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        request_meta=meta,
    )


@router.post("/login", response_model=AuthResponse, summary="Log in with email & password")
async def login(
    payload: UserLogin,
    service: AuthServiceDep,
    meta: RequestMeta,
) -> AuthResponse:
    return await service.login(
        email=payload.email,
        password=payload.password,
        request_meta=meta,
    )


@router.post("/refresh", response_model=TokenPair, summary="Rotate a refresh token")
async def refresh(
    payload: RefreshRequest,
    service: AuthServiceDep,
    meta: RequestMeta,
) -> TokenPair:
    return await service.refresh(refresh_token=payload.refresh_token, request_meta=meta)


@router.post("/logout", response_model=Message, summary="Revoke a refresh token")
async def logout(
    payload: LogoutRequest,
    service: AuthServiceDep,
    meta: RequestMeta,
) -> Message:
    await service.logout(refresh_token=payload.refresh_token, request_meta=meta)
    return Message(detail="Logged out successfully.")


@router.get("/me", response_model=UserPublic, summary="Get the current user")
async def me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)
