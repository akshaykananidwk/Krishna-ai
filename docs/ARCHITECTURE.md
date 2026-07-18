# Architecture

Krishna AI is a two-tier system: a **Flutter** Android client and a **FastAPI**
backend, backed by PostgreSQL, Redis, and Qdrant.

```
┌─────────────────────────────┐         HTTPS / JWT          ┌──────────────────────────────┐
│      Flutter app (Android)  │  ───────────────────────────▶ │        FastAPI backend        │
│                             │                               │                              │
│  presentation → domain      │                               │  API → services → repos      │
│        ▲          ▲         │  ◀─────────────────────────── │        │         │            │
│        └── data ──┘         │        JSON responses         │   Postgres  Redis  Qdrant     │
└─────────────────────────────┘                               └──────────────────────────────┘
```

## Backend layering

The backend follows a clean, dependency-inverted layering:

```
HTTP request
   │
   ▼
API endpoint (app/api/v1/endpoints)     ← FastAPI routing, request/response schemas
   │  depends on
   ▼
Service (app/services)                  ← business logic, raises domain exceptions
   │  depends on
   ▼
Repository (app/repositories)           ← all SQLAlchemy queries live here
   │  uses
   ▼
Models (app/models)                     ← ORM entities (portable column types)
```

Cross-cutting concerns live in `app/core`:

- `config.py` — typed settings from env (`pydantic-settings`).
- `security.py` — password hashing + JWT create/decode (framework-free).
- `crypto.py` — AES-256-GCM field encryption.
- `database.py` — async engine + `get_db` dependency (commit/rollback contract).
- `redis_client.py` — shared async Redis client.
- `rate_limit.py` — fixed-window rate-limit middleware (fails open).
- `exceptions.py` — domain errors mapped to HTTP responses by a single handler.

**Why services raise domain exceptions, not `HTTPException`:** it keeps business
logic transport-agnostic and unit-testable. `app/main.py` registers one handler
that turns any `AppError` into `{error_code, detail}` with the right status.

### Request lifecycle (login)

1. `POST /api/v1/auth/login` hits `endpoints/auth.py`.
2. Dependencies build a `UserRepository` (bound to a request-scoped
   `AsyncSession`) and an `AuthService`.
3. `AuthService.login` fetches the user, verifies the password in constant time
   (even for unknown emails), issues an access token + a rotating refresh token,
   stores the refresh token's **hash**, and writes an audit-log row.
4. `get_db` commits the transaction as the request unwinds.

## Mobile layering (Clean Architecture)

```
presentation (pages, widgets, Riverpod controllers)
     │ depends on
     ▼
domain (entities, repository interfaces, use cases)   ← pure Dart, no Flutter
     ▲ implemented by
     │
data (models, remote data source, repository impl)    ← Dio + secure storage
```

State & DI are handled by **Riverpod** providers; navigation by **go_router**
with an auth-aware `redirect`. The `AuthInterceptor` transparently refreshes an
expired access token once and retries the original request, coalescing
concurrent refreshes.

## Security

| Concern | Approach |
|---------|----------|
| Password storage | bcrypt via passlib |
| Session tokens | Short-lived JWT access + long-lived **rotating** refresh |
| Refresh token storage | SHA-256 hash in DB → server-side revocation, leak-resistant |
| Account enumeration | Constant-time login verifies a dummy hash for unknown users |
| Data at rest | AES-256-GCM helpers for sensitive columns |
| Transport | HTTPS; HSTS + `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` headers |
| Abuse | Redis fixed-window rate limiting per client/path |
| Auditing | Append-only `audit_logs` for auth events |
| Mobile secrets | Android Keystore-backed `EncryptedSharedPreferences` |
| Federated identity | Firebase-ready (`firebase_uid` column, token-exchange schema) |

## Memory Engine & RAG (Module 4)

The memory engine turns any data source (conversations, notes, meetings, …)
into vector-searchable knowledge. Two provider abstractions keep it swappable:

- **`EmbeddingProvider`** (`app/services/embeddings`): `local` (deterministic,
  dependency-free — dev/test), `openai`, `gemini`. Selected by
  `EMBEDDING_PROVIDER`; never hardcoded.
- **`VectorStore`** (`app/services/vectorstore`): `qdrant` (production) or
  `memory` (in-process cosine — dev/test). Selected by `VECTOR_STORE`.

PostgreSQL stays the source of truth; the vector store holds only vectors keyed
by `memory_items.id`, with a payload (`user_id`, `source_type`, `tags`,
`status`, `created_at`) used for filtered, isolated search.

```
create memory ─▶ persist (PG) ─▶ embed ─▶ upsert vector (+dedupe link)
                                     └▶ record embedding status (ready/failed)

RAG query ─▶ embed ─▶ vector search ─▶ rank ─▶ context build ─▶ prompt ─▶ LLM ─▶ SSE
```

**Ranking** (`services/memory/ranking.py`, pure/testable) blends similarity,
recency (exponential decay), importance, access frequency, feedback, and a
pinned boost. **Context building** (`context_builder.py`) bounds prompt size by
a character budget, prioritising the highest-ranked memories.

**RAG reuses the AI-Chat `LLMClient` by composition** — the existing chat module
is untouched; `/rag/query` is the memory-aware assistant.

**Background workers** (`services/memory/maintenance.py`) — `cleanup_deleted`,
`retry_failed_embeddings`, `reindex_user` — are dependency-injected async
functions (testable) with thin `run_*` production wrappers that own a DB session.
In production these run under cron or a Celery/RQ worker.

## Scalability notes

- **Stateless API**: horizontal scaling behind a load balancer; sessions live in
  Postgres/Redis, not app memory.
- **Async I/O**: SQLAlchemy async + asyncpg for high concurrency.
- **Vector search** (Qdrant) is provisioned in the stack for upcoming RAG/memory
  modules.
- **Portable column types** (`app/models/types.py`) let the same models run on
  Postgres (prod) and SQLite (fast, service-free tests).
