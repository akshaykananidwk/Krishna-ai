"""Krishna AI backend — FastAPI application factory & entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis_client import close_redis
from app.schemas.common import HealthStatus


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup hooks (warm caches, verify connections) can go here.
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=__version__,
        description="Krishna AI — advanced AI personal assistant backend.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---- Middleware ---- #
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RateLimitMiddleware)

    # ---- Security headers ---- #
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ---- Domain error handler ---- #
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "detail": exc.detail},
        )

    # ---- Routes ---- #
    @app.get("/health", response_model=HealthStatus, tags=["System"])
    async def health() -> HealthStatus:
        return HealthStatus(status="ok", version=__version__, environment=settings.ENVIRONMENT)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
