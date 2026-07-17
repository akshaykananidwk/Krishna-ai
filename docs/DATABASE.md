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

## Entity relationships

```
users 1 ──────< refresh_tokens        (cascade delete)
users 1 ──────< audit_logs            (set null on delete)
users 1 ──────< conversations 1 ──< messages   (cascade delete)
```

## Planned tables (future modules)

`sessions`, `conversations`, `messages`, `memories`, `embeddings`, `notes`,
`tasks`, `reminders`, `meetings`, `documents`, `files`, `notifications`,
`settings`. Vector embeddings will live in **Qdrant**, referenced by id from
Postgres. See [`ROADMAP.md`](ROADMAP.md).
