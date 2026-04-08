# telegram-AI

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
