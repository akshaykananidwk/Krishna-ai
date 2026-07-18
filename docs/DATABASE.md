# Database

PostgreSQL 16 is the primary datastore. Schema changes are managed with
**Alembic**; models use portable column types so the test suite can run on
SQLite.

## Migrations

```bash
cd backend
alembic upgrade head              # apply all migrations
alembic revision --autogenerate -m "add notes"   # create a new migration
alembic downgrade -1              # roll back one
```

Migration `0001_initial_auth` creates the Module 1 tables below.

## Module 1 schema

### `users`

| Column           | Type          | Notes                                   |
|------------------|---------------|-----------------------------------------|
| id               | UUID (PK)     | generated in app                        |
| email            | varchar(320)  | unique, indexed, lowercased             |
| hashed_password  | varchar(255)  | nullable (null for pure-federated users)|
| full_name        | varchar(255)  | nullable                                |
| firebase_uid     | varchar(128)  | unique, nullable — federated identity   |
| is_active        | boolean       | default true                            |
| is_verified      | boolean       | default false                           |
| is_superuser     | boolean       | default false                           |
| last_login_at    | timestamptz   | nullable                                |
| created_at       | timestamptz   | server default now()                    |
| updated_at       | timestamptz   | server default now(), on update         |

### `refresh_tokens`

| Column      | Type         | Notes                                       |
|-------------|--------------|---------------------------------------------|
| id          | UUID (PK)    |                                             |
| user_id     | UUID (FK)    | → `users.id`, ON DELETE CASCADE, indexed    |
| token_hash  | varchar(64)  | **SHA-256 of the raw token**, unique        |
| expires_at  | timestamptz  |                                             |
| revoked_at  | timestamptz  | nullable — set on rotation/logout           |
| created_at  | timestamptz  |                                             |
| updated_at  | timestamptz  |                                             |

Composite index `ix_refresh_tokens_user_active (user_id, revoked_at)` supports
"revoke all active sessions for a user".

### `audit_logs`

| Column      | Type          | Notes                                       |
|-------------|---------------|---------------------------------------------|
| id          | UUID (PK)     |                                             |
| user_id     | UUID (FK)     | → `users.id`, ON DELETE SET NULL, indexed   |
| action      | varchar(64)   | indexed — e.g. `login`, `login_failed`, `logout`, `token_refresh`, `register` |
| detail      | varchar(512)  | nullable                                    |
| ip_address  | INET          | nullable                                    |
| user_agent  | varchar(512)  | nullable                                    |
| created_at  | timestamptz   | server default now()                        |

## Module 3 schema (AI Chat) — migration `0002_chat`

### `conversations`

| Column          | Type         | Notes                                   |
|-----------------|--------------|-----------------------------------------|
| id              | UUID (PK)    |                                         |
| user_id         | UUID (FK)    | → `users.id`, ON DELETE CASCADE, indexed|
| title           | varchar(200) | default `New chat`; auto-set from first message |
| last_message_at | timestamptz  | nullable; drives recency ordering       |
| archived_at     | timestamptz  | nullable                                |
| created_at / updated_at | timestamptz | server-managed                   |

Composite index `ix_conversations_user_recent (user_id, last_message_at)`.

### `messages`

| Column          | Type         | Notes                                   |
|-----------------|--------------|-----------------------------------------|
| id              | UUID (PK)    |                                         |
| conversation_id | UUID (FK)    | → `conversations.id`, ON DELETE CASCADE, indexed |
| role            | varchar(16)  | `user` / `assistant` / `system`         |
| content         | text         |                                         |
| model           | varchar(64)  | nullable; set on assistant messages     |
| token_count     | integer      | nullable                                |
| created_at      | timestamptz  | server default now()                    |

## Module 4 schema (Memory Engine) — migration `0003_memory`

PostgreSQL is the **source of truth**; Qdrant holds only vectors keyed by
`memory_items.id`. All tables are user-scoped.

| Table | Purpose |
|-------|---------|
| `memory_items` | Source of truth for a memory: content, `source_type`, `importance`, `pinned`, `status` (active/archived/deleted), access counters, soft-delete timestamps |
| `memory_embeddings` | Per-memory embedding record: provider, model, dim, `vector_id`, `status` (pending/ready/failed), `attempts` — drives the retry worker |
| `memory_tags` | Tags (manual or `auto`), unique per (memory, tag) |
| `memory_collections` + `memory_collection_items` | User-defined groupings (many-to-many) |
| `memory_bookmarks` | User bookmarks, unique per (user, memory) |
| `memory_feedback` | `+1`/`-1` relevance signal per (user, memory) — feeds ranking |
| `memory_links` | Relationships between memories (`related` / `duplicate`) with a score |
| `memory_metadata` | Arbitrary **AES-256-GCM-encrypted** key/value metadata |
| `memory_search_logs` | Per-search audit + analytics (query, result count, latency) |
| `knowledge_sources` | Distinct ingestion origins, unique per (user, type, external_ref) — dedupes imports |

Key indexes: `ix_memory_items_user_status`, `ix_memory_items_user_type`,
`ix_memory_tags_tag`. Soft-deleted rows are purged by the cleanup worker after
`MEMORY_RETENTION_DAYS`.

## Entity relationships

```
users 1 ──────< refresh_tokens        (cascade delete)
users 1 ──────< audit_logs            (set null on delete)
users 1 ──────< conversations 1 ──< messages   (cascade delete)
users 1 ──────< memory_items 1 ──1 memory_embeddings   (cascade delete)
memory_items 1 ──< memory_tags / memory_metadata / memory_links
users 1 ──────< memory_collections 1 ──< memory_collection_items >── memory_items
```

## Planned tables (future modules)

`sessions`, `conversations`, `messages`, `memories`, `embeddings`, `notes`,
`tasks`, `reminders`, `meetings`, `documents`, `files`, `notifications`,
`settings`. Vector embeddings will live in **Qdrant**, referenced by id from
Postgres. See [`ROADMAP.md`](ROADMAP.md).
