# Testing Guide

## Backend

The suite runs against **in-memory SQLite** — no Postgres/Redis needed — thanks
to portable column types and a fake Redis fixture.

```bash
cd backend
source .venv/bin/activate
pytest                                  # all tests
pytest --cov=app --cov-report=term-missing
pytest tests/test_auth_api.py -k login  # filter
```

### What's covered (Module 1)

- **`test_security.py`** — password hashing, JWT create/decode, token-type
  enforcement, unique `jti`, AES-256-GCM roundtrip + non-determinism.
- **`test_auth_api.py`** — register (success/duplicate/weak password), login
  (success/wrong password/unknown user), `/me` (auth required + happy path),
  refresh **rotation** + reuse rejection, logout revocation, invalid bearer.

### Fixtures (`tests/conftest.py`)

- `db_engine` / `db_session` — fresh in-memory schema per test.
- `client` — `httpx.AsyncClient` over the ASGI app with `get_db` overridden and
  Redis swapped for an in-memory fake.
- `valid_user_payload` — a reusable registration body.

### Layout for new tests

Mirror the app structure: service logic → `tests/test_<module>_service.py`,
endpoints → `tests/test_<module>_api.py`. Prefer testing behaviour through the
API and services; test repositories directly only for non-trivial queries.

## Mobile

```bash
cd mobile
flutter test                # unit + widget tests
flutter test --coverage     # writes coverage/lcov.info
flutter analyze             # static analysis
```

### What's covered (Module 1)

- **`validators_test.dart`** — email/password/confirm rules.
- **`auth_repository_impl_test.dart`** — success persists tokens; 401 → `AuthFailure`
  without persisting; timeout → `NetworkFailure`; logout clears tokens even when
  the server call fails. Uses **mocktail** to fake the data source and storage.
- **`login_page_test.dart`** — empty-form validation and password-visibility toggle.

### Conventions

- Use `mocktail` for mocks; override Riverpod providers with `ProviderScope`
  `overrides` in widget tests.
- Keep the **domain** layer covered by pure Dart unit tests (no Flutter binding).

## Continuous integration

Both suites run in GitHub Actions on every push/PR. Coverage artifacts are
uploaded per job. See [`DEPLOYMENT.md`](DEPLOYMENT.md#cicd).
