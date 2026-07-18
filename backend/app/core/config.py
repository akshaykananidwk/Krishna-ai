"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
via ``pydantic-settings``. Everything the app needs is centralised here so that
no module reads ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Application ----
    PROJECT_NAME: str = "Krishna AI"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)

    # ---- Security / JWT ----
    SECRET_KEY: str = "insecure-dev-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # ---- Field-level encryption ----
    ENCRYPTION_KEY: str = "0" * 64

    # ---- PostgreSQL ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "krishna"
    POSTGRES_PASSWORD: str = "krishna_dev_password"
    POSTGRES_DB: str = "krishna_ai"

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ---- Qdrant ----
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # ---- Rate limiting ----
    RATE_LIMIT_PER_MINUTE: int = 60

    # ---- Firebase ----
    FIREBASE_CREDENTIALS_PATH: str = ""

    # ---- AI / Anthropic (Module: AI Chat) ----
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    AI_MAX_TOKENS: int = 4096
    # Upper bound on prior turns replayed to the model (keeps context bounded).
    AI_HISTORY_LIMIT: int = 40
    AI_SYSTEM_PROMPT: str = (
        "You are Krishna, a helpful, concise, privacy-respecting AI personal "
        "assistant. Answer clearly and cite uncertainty honestly."
    )

    # ---- Memory Engine (Module 4: Memory + Vector Search + RAG) ----
    # Embeddings: "local" (dependency-free, deterministic — dev/test default),
    # "openai", or "gemini". Providers are never hardcoded; see services/embeddings.
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = ""  # blank = provider default
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LOCAL_EMBEDDING_DIM: int = 256

    # Vector store: "memory" (in-process cosine — dev/test) or "qdrant".
    VECTOR_STORE: str = "memory"
    QDRANT_COLLECTION: str = "krishna_memory"

    # Retrieval / RAG
    RAG_TOP_K: int = 8
    RAG_MIN_SCORE: float = 0.15
    RAG_MAX_CONTEXT_CHARS: int = 6000
    # Duplicate detection threshold (cosine similarity).
    MEMORY_DUPLICATE_THRESHOLD: float = 0.92
    # Days a soft-deleted memory is retained before the cleanup worker purges it.
    MEMORY_RETENTION_DAYS: int = 30

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow CORS origins to be provided as a comma-separated string."""
        if isinstance(value, str) and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy sync URL (used by Alembic migrations)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async URL (used by the running application)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()


settings = get_settings()
