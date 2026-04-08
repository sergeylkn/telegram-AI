# telegram-AI

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
