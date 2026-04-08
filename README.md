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
