# telegram-AI

A Telegram support bot skeleton with AI auto-reply and manager handoff mode.

## Architecture

The project is designed around four runtime services:

- **app**: Python bot/service process (webhook receiver + handoff state machine).
- **Postgres**: persistent relational storage (users, chats, summaries, handoff audit).
- **Redis**: short-lived state/cache (rate limits, session pointers, queues).
- **Ollama**: local LLM inference endpoint for AI responses.

### Handoff state model

Each chat has a mode:

1. `ai` (default): user messages can trigger AI responses.
2. `manual`: manager has taken over; user messages no longer trigger AI.

Transitions:

- **Default** → `ai`
- **Manager takeover API or first manager message** → `manual`
- **Manager switch-back action** → `ai`

Context assembly for AI requests:

1. Optional rolling **summary** (prepended as system context).
2. Last `N` messages from the recent window.

## Environment variables

Copy `.env.example` to `.env` and set values:

```bash
cp .env.example .env
```

Included categories:

- Telegram: bot token, webhook secret, webhook URL
- Postgres: host/port/user/password/db + full URL
- Redis: host/port/db + full URL
- Ollama: URL, model, timeout
- Admin auth: admin token and manager user ids
- Runtime: host/port/log level

## Run with Docker Compose

```bash
docker compose up --build
```

This starts:

- App on `http://localhost:8080`
- Postgres on `localhost:5432`
- Redis on `localhost:6379`
- Ollama on `localhost:11434`

## Local test suite (pytest)

```bash
python -m pytest
```

Covered behavior:

- AI default active
- manager takeover flow
- first manager message disables AI
- user messages in manual mode do not trigger AI
- switch back to AI
- multi-chat state isolation
- context assembly with summary + recent window

## Webhook/API examples

### Register Telegram webhook

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.example/webhook/telegram",
    "secret_token": "replace_me"
  }'
```

### Incoming webhook shape (example)

```json
{
  "update_id": 123456,
  "message": {
    "message_id": 42,
    "chat": {"id": 10001, "type": "private"},
    "from": {"id": 555111, "is_bot": false},
    "text": "Hello"
  }
}
```

### Manager takeover API (example)

```bash
curl -X POST http://localhost:8080/api/handoff/takeover \
  -H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":10001,"manager_id":9001}'
```

### Switch chat back to AI (example)

```bash
curl -X POST http://localhost:8080/api/handoff/ai \
  -H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":10001}'
```

## Handoff sequence walkthrough

1. User sends first message in a new chat.
2. Chat mode is `ai` by default, so AI replies.
3. Manager joins and sends first manager message (or calls takeover API).
4. System flips chat mode to `manual` and records `manager_id`.
5. User sends new messages; AI is suppressed while manager handles chat.
6. Manager triggers switch-back action.
7. Chat mode returns to `ai`; subsequent user messages trigger AI again.

## Project files

- `app.py`: in-memory handoff engine and context assembly function.
- `tests/test_handoff_flow.py`: pytest suite for handoff + context rules.
- `Dockerfile`: app container build.
- `docker-compose.yml`: multi-service local stack.
- `.env.example`: required env variables reference.
Internal admin controls for supervised chat handoff are implemented in `admin_api.py`.

## Implemented authenticated admin endpoints (service methods)

- `list_active_chats(ctx)`
- `get_chat_details(ctx, chat_id, history_limit=20)`
- `switch_chat_to_manual_mode(ctx, chat_id, reason='operator_override')`
- `return_chat_to_ai_mode(ctx, chat_id, reason='operator_release')`
- `assign_manager(ctx, chat_id, manager_id)`
- `unassign_manager(ctx, chat_id)`
- `post_manager_message(ctx, chat_id, manager_id, content)`

All methods require a valid `AdminContext` with the configured internal token.

## Event logging

Operator actions are tracked in SQLite tables:

- `mode_events` for AI/manual mode transitions.
- `handoff_events` for manager assignment/handoff/message actions.

The `post_manager_message` method enforces controlled manager message delivery and triggers first-message takeover behavior by switching AI mode to manual when needed.

## Running tests

```bash
python -m unittest discover -s tests -v
```
Core service scaffolding for a Telegram AI assistant:

- `AIService` interface with Ollama adapter.
- `MemoryService` for context assembly (recent messages, summary snapshot, metadata).
- Summary update policy to cap context growth.
- Prompt policy enforcing live-manager tone and uncertainty handling.
- Orchestrator enforcing mode/handoff business logic before AI invocation.

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
Initial FastAPI project scaffold for a Telegram + AI orchestration service.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python run.py
```

## Project layout

- `app/api`: external HTTP endpoints (Telegram webhook + admin controls)
- `app/core`: configuration and logging setup
- `app/domain`: deterministic business rules/state machine
- `app/services`: orchestration and provider abstractions
- `app/infrastructure`: db/repositories/telegram/redis adapters
