# Deployment Guide

## Local stack (Docker Compose)

```bash
cp backend/.env.example backend/.env     # set SECRET_KEY, ENCRYPTION_KEY, passwords
docker compose up -d --build
docker compose exec api alembic upgrade head   # if not auto-run
```

Services:

| Service  | Port  | Purpose                    |
|----------|-------|----------------------------|
| api      | 8000  | FastAPI (Swagger at /docs) |
| postgres | 5432  | primary database           |
| redis    | 6379  | cache + rate limiting      |
| qdrant   | 6333  | vector search (future)     |

The `api` container runs `alembic upgrade head` then `uvicorn` on start.

## Environment variables

See [`backend/.env.example`](../backend/.env.example). Generate secrets:

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # ENCRYPTION_KEY (must be 64 hex chars = 32 bytes)
```

**Never commit `.env`.** In production, inject secrets via your platform's
secret manager (not files baked into images).

## Production checklist

- [ ] `ENVIRONMENT=production`, unique `SECRET_KEY` and `ENCRYPTION_KEY`.
- [ ] Managed Postgres with automated backups + PITR.
- [ ] Redis with persistence/HA as needed.
- [ ] TLS termination at the load balancer; HSTS is already sent by the app.
- [ ] Restrict `BACKEND_CORS_ORIGINS` to known client origins.
- [ ] Run multiple `uvicorn`/`gunicorn` workers behind the LB; the API is stateless.
- [ ] Ship logs/metrics to your observability stack; alert on `login_failed` spikes.
- [ ] Set container resource limits and health checks (the image has a `HEALTHCHECK`).

## Building the API image

```bash
docker build -t krishna-ai-backend:latest ./backend
docker run -p 8000:8000 --env-file backend/.env krishna-ai-backend:latest
```

The image is multi-stage (builder + slim runtime), runs as a **non-root** user,
and includes a container `HEALTHCHECK` against `/health`.

## Mobile release

```bash
cd mobile
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://api.krishna.example.com
```

Upload the resulting `.aab` to the Google Play Console. Configure app signing,
and add Firebase config (`google-services.json`) when the Firebase-backed
auth/messaging modules are enabled.

## CI/CD

GitHub Actions run on every push/PR (see `.github/workflows`):

- **backend-ci** — Ruff lint + format check, mypy (advisory), pytest w/ coverage,
  Docker build.
- **mobile-ci** — `dart format` check, `flutter analyze`, `flutter test` w/ coverage.
