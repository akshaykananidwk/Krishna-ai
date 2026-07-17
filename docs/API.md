# API Reference

Base URL: `{host}/api/v1`  ·  Interactive docs: `GET /docs` (Swagger) and
`GET /redoc`. OpenAPI JSON: `GET /api/v1/openapi.json`.

All request/response bodies are JSON. Errors use a consistent envelope:

```json
{ "error_code": "invalid_credentials", "detail": "The email or password is incorrect." }
```

Validation errors (422) use FastAPI's standard schema.

## System

### `GET /health`
Returns service status.
```json
{ "status": "ok", "version": "0.1.0", "environment": "development" }
```

## Authentication — `/auth`

### `POST /auth/register` → `201`
Create an account and receive tokens.

Request:
```json
{ "email": "arjuna@example.com", "password": "Dharma123", "full_name": "Arjuna" }
```
Password policy: ≥ 8 chars, with a lowercase, an uppercase, and a digit.

Response `201`:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "1f2e...", "email": "arjuna@example.com",
    "full_name": "Arjuna", "is_active": true, "is_verified": false,
    "created_at": "2026-07-17T10:00:00Z", "last_login_at": "2026-07-17T10:00:00Z"
  }
}
```
Errors: `409 email_already_registered`, `422` validation.

### `POST /auth/login` → `200`
```json
{ "email": "arjuna@example.com", "password": "Dharma123" }
```
Returns the same shape as register. Errors: `401 invalid_credentials`,
`403 inactive_user`.

### `POST /auth/refresh` → `200`
Rotate a refresh token. The presented token is **revoked** and a new pair is
issued.
```json
{ "refresh_token": "eyJhbGci..." }
```
Response:
```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```
Errors: `401 invalid_token` (expired, unknown, or already-rotated token).

### `POST /auth/logout` → `200`
Revoke a refresh token.
```json
{ "refresh_token": "eyJhbGci..." }
```
```json
{ "detail": "Logged out successfully." }
```

### `GET /auth/me` → `200`
Requires `Authorization: Bearer <access_token>`. Returns the current user
(`UserPublic`). Errors: `401 invalid_token`, `403 inactive_user`.

## Auth flow

```
register/login ──▶ { access, refresh }
      │
      ├─ use access token in Authorization header
      │
      └─ on 401 ──▶ POST /auth/refresh ──▶ new { access, refresh }  (old refresh revoked)
```

## AI Chat — `/chat`

All routes require `Authorization: Bearer <access_token>`. Conversations and
messages are scoped to the authenticated user.

### `POST /chat/conversations` → `201`
Create an (optionally titled) conversation.
```json
{ "title": "Trip planning" }
```
Returns a `ConversationSummary`: `{ id, title, last_message_at, created_at, updated_at }`.

### `GET /chat/conversations` → `200`
List the user's conversations (most-recent first), each a `ConversationSummary`.

### `GET /chat/conversations/{id}` → `200`
Return the conversation plus its `messages` (`{ id, role, content, model, created_at }`).
`404 not_found` if it doesn't exist or belongs to another user.

### `PATCH /chat/conversations/{id}` → `200`
Rename: `{ "title": "New name" }`.

### `DELETE /chat/conversations/{id}` → `200`
`{ "detail": "Conversation deleted." }`.

### `POST /chat/conversations/{id}/messages` → `200` (Server-Sent Events)
Send a user message and **stream** the assistant reply. Response
`Content-Type: text/event-stream`. Request: `{ "content": "..." }`.

Each SSE frame is `data: <json>\n\n`, where `<json>` is one of:
```
{ "type": "start", "conversation_id": "..." }
{ "type": "delta", "text": "partial text" }
{ "type": "done",  "message_id": "...", "content": "full text", "model": "claude-opus-4-8" }
{ "type": "error", "detail": "..." }
```
The user message and the final assistant message are persisted; the first
message auto-titles the conversation. Returns `503 ai_unavailable` (before the
stream starts) if `ANTHROPIC_API_KEY` is unset.

## Rate limiting

Fixed-window per client IP + path (default 60 req/min). Responses include
`X-RateLimit-Limit` / `X-RateLimit-Remaining`; exceeding the limit returns
`429` with `Retry-After: 60`.
