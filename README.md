# telegram-AI

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
