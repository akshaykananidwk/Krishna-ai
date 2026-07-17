# Developer Guide

## Prerequisites

- Python 3.11+, Docker
- Flutter 3.4+ (Dart 3.4+)

## Backend conventions

- **Layering:** endpoint → service → repository → model. Never query the ORM
  from an endpoint; never put HTTP concerns in a service.
- **Errors:** raise `AppError` subclasses (`app/core/exceptions.py`) from
  services. The global handler renders `{error_code, detail}`.
- **Schemas:** request/response models live in `app/schemas`. Never return an
  ORM object directly — map to a Pydantic model (e.g. `UserPublic`), which also
  guarantees secrets like `hashed_password` are never serialized.
- **Settings:** read config only via `app.core.config.settings`.
- **Style:** `ruff check` + `ruff format` (line length 100). Run before commit.

### Adding a new backend module (recipe)

1. **Model** — add ORM classes in `app/models/<module>.py`; export from
   `app/models/__init__.py` so Alembic sees them.
2. **Migration** — `alembic revision --autogenerate -m "add <module>"`, review,
   then `alembic upgrade head`.
3. **Schemas** — `app/schemas/<module>.py`.
4. **Repository** — `app/repositories/<module>_repository.py` (all queries).
5. **Service** — `app/services/<module>_service.py` (business rules).
6. **Endpoints** — `app/api/v1/endpoints/<module>.py`; register the router in
   `app/api/v1/router.py`.
7. **Tests** — `tests/test_<module>_*.py`.
8. **Docs** — update `API.md`, `DATABASE.md`, `ROADMAP.md`.

## Mobile conventions

- **Clean Architecture:** `presentation → domain ← data`. The domain layer must
  not import Flutter, Dio, or storage packages.
- **State/DI:** Riverpod providers. Expose use cases via providers; controllers
  are `StateNotifier`s with sealed state classes.
- **Errors:** data sources throw exceptions; repositories convert them to
  `Either<Failure, T>` (dartz). UI switches on `Failure`/state.
- **Navigation:** add routes in `core/router/app_router.dart`; use typed
  `Routes` constants.
- **Style:** `dart format .` + `flutter analyze` (see `analysis_options.yaml`).

### Adding a new mobile feature (recipe)

```
features/<feature>/
├── data/{datasources,models,repositories}
├── domain/{entities,repositories,usecases}
└── presentation/{providers,pages,widgets}
```

1. Define the **entity** and **repository interface** in `domain`.
2. Implement **models + data source + repository** in `data`.
3. Wire **providers** and build **pages/widgets** in `presentation`.
4. Add a route + guard in `core/router`.
5. Add unit tests (domain/data) and widget tests (presentation).

## Git & CI

- Feature branches; keep commits focused with descriptive messages.
- CI must be green (lint, format, tests) before merge.
- Follow the incremental model plan in [`ROADMAP.md`](ROADMAP.md): one fully
  tested and documented module per change set.
