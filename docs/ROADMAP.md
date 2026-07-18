# Roadmap

Krishna AI is delivered **incrementally**: each module ships with requirements,
architecture, data model, API, UI, business logic, tests, and docs before the
next begins.

## Legend
✅ done · 🚧 in progress · ⬜ planned

## Foundation
- ✅ Monorepo structure, docs, CI (backend + mobile), Docker stack
  (Postgres + Redis + Qdrant + API)
- ✅ Backend core: config, async DB, Redis, security (JWT/bcrypt), AES-256-GCM,
  rate limiting, security headers, domain-error handling, audit logging
- ✅ Mobile core: Clean Architecture, Riverpod DI, Dio + refresh interceptor,
  secure token storage, Material 3 theme, auth-aware routing
- ✅ AI layer: provider-agnostic `LLMClient` (Anthropic Claude), streamed
  Server-Sent-Events chat, conversation persistence
- ✅ Memory Engine: provider-agnostic embeddings (local / OpenAI / Gemini) and
  vector store (Qdrant / in-memory), semantic + filtered search, multi-signal
  ranking, streaming RAG, background maintenance workers

## Modules

| # | Module | Status |
|---|--------|--------|
| 1 | Authentication | ✅ done |
| 2 | User Profile | ⬜ |
| 3 | AI Chat | ✅ done |
| 6 | Conversation History | ✅ done (with AI Chat) |
| 4 | Voice Input | ⬜ |
| 5 | Speech-to-Text | ⬜ |
| 6 | Text-to-Speech | ⬜ |
| 7 | Notes | ⬜ |
| 8 | Smart Notes | ⬜ |
| 9 | Meeting Summaries | ⬜ |
| 10 | Tasks | ⬜ |
| 11 | Reminders | ⬜ |
| 12 | Calendar | ⬜ |
| 13 | Personal Knowledge Base | ✅ done (Memory Engine) |
| 14 | Semantic Search | ✅ done (Memory Engine) |
| 15 | AI Memory | ✅ done (Memory Engine + RAG) |
| 16 | OCR | ⬜ |
| 17 | Image Understanding | ⬜ |
| 18 | Document Analysis | ⬜ |
| 19 | PDF Chat | ⬜ |
| 20 | Email Assistant | ⬜ |
| 21 | Daily Planner | ⬜ |
| 22 | Weekly Planner | ⬜ |
| 23 | Habit Tracker | ⬜ |
| 24 | Goals | ⬜ |
| 25 | Notifications | ⬜ |
| 26 | Offline Mode | ⬜ |
| 27 | Cloud Sync | ⬜ |
| 28 | Settings | ⬜ |
| 29 | Privacy Controls | ⬜ |
| 30 | Backup & Restore | ⬜ |

## Suggested sequencing

The modules build on each other; a pragmatic order after Authentication:

1. **User Profile** (2) — extends the user model; small, validates the CRUD +
   settings patterns.
2. **AI Chat** (3) + **AI Memory/RAG** (13–15) — the assistant core, introduces
   Qdrant and streaming.
3. **Notes/Tasks/Reminders** (7, 10, 11) — productivity CRUD with offline-first
   sync (26, 27).
4. **Voice** (4–6) and **Document/Image** (16–19) — heavier device + AI
   integrations.
5. **Planners, Habits, Goals** (21–24), then **Notifications** (25),
   **Settings/Privacy/Backup** (28–30).

Each will follow the recipes in [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md).
