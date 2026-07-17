<div align="center">

# 🕉️ Krishna AI

**An advanced, privacy-first AI personal assistant for Android.**

Productivity · Voice · Personal knowledge · Meeting intelligence · Task management

[![Backend CI](https://img.shields.io/badge/backend-CI-blue)](.github/workflows/backend-ci.yml)
[![Mobile CI](https://img.shields.io/badge/mobile-CI-blue)](.github/workflows/mobile-ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

## What is Krishna AI?

Krishna AI is a modular, production-oriented personal assistant. It pairs a
**Flutter (Material 3)** Android app with a **FastAPI** backend, **PostgreSQL**,
**Redis**, and **Qdrant** for vector search. It is designed around 30 feature
modules (chat, voice, notes, meetings, tasks, RAG-based memory, and more),
delivered **incrementally** — one fully-tested module at a time.

> **Status:** Foundation + **Module 1 (Authentication)** complete and tested.
> See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the module plan and progress.

## Repository structure

```
Krishna-ai/
├── backend/            # FastAPI service (API, models, services, migrations, tests)
├── mobile/             # Flutter app (Clean Architecture + Riverpod)
├── docs/               # Architecture, database, API, deployment, testing guides
├── .github/workflows/  # CI for backend and mobile
└── docker-compose.yml  # Local stack: Postgres + Redis + Qdrant + API
```

## Tech stack

| Layer         | Technology                                                        |
|---------------|-------------------------------------------------------------------|
| Mobile        | Flutter, Dart, Material 3, Riverpod, go_router, Dio                |
| Backend       | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic                |
| Data          | PostgreSQL 16, Redis 7, Qdrant (vector DB)                         |
| Auth/Security | JWT (access + rotating refresh), bcrypt, AES-256-GCM, Firebase-ready |
| Infra / CI    | Docker, docker-compose, GitHub Actions, Ruff, pytest, flutter test |

## Quick start

### 1. Backend + infrastructure (Docker)

```bash
cp backend/.env.example backend/.env      # then edit secrets
docker compose up -d                      # Postgres, Redis, Qdrant, API
# API docs: http://localhost:8000/docs
```

### 2. Backend (local, without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# Point .env at a running Postgres, then:
alembic upgrade head
uvicorn app.main:app --reload
pytest                                     # run the test suite
```

### 3. Mobile app

```bash
cd mobile
flutter create .                           # generate android/ios scaffolding
flutter pub get
flutter run                                # emulator reaches host at 10.0.2.2
```

## Module 1 — Authentication (implemented)

- Email/password **register**, **login**, **refresh** (with token rotation),
  **logout**, and **`/me`**.
- **Rotating refresh tokens** persisted as SHA-256 hashes → server-side
  revocation and leak resistance.
- **bcrypt** password hashing; **timing-safe** login that doesn't reveal which
  emails are registered.
- **AES-256-GCM** helpers for field-level encryption at rest.
- **Rate limiting**, **security headers**, **audit logging**, and Firebase-ready
  federated-identity columns.
- Mobile: secure Keystore-backed token storage, transparent refresh-and-retry
  interceptor, auth-aware routing, Material 3 login/register UI.

## Documentation

| Doc | Contents |
|-----|----------|
| [Architecture](docs/ARCHITECTURE.md) | System design, layering, request lifecycle |
| [Database](docs/DATABASE.md)         | Schema, tables, migrations |
| [API](docs/API.md)                   | Endpoint reference for the auth module |
| [Deployment](docs/DEPLOYMENT.md)     | Docker, environment, production notes |
| [Testing](docs/TESTING.md)           | How to run and write tests |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Conventions, adding a module |
| [Roadmap](docs/ROADMAP.md)           | The 30-module plan & status |

## Security & privacy

Privacy-first defaults, encrypted local storage, secure token handling, rate
limiting, and audit trails are built in from Module 1. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#security) for the security model.

## License

Released under the [MIT License](LICENSE).
