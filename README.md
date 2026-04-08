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
