"""Conversation context windowing and summary strategy."""


class MemoryService:
    """Handles retrieval/truncation/persistence for conversational memory."""

    def __init__(self, max_turns: int = 12):
        self.max_turns = max_turns

    async def build_context(self, chat_id: int, incoming_text: str) -> list[dict[str, str]]:
        """Build model-ready context window for chat."""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": incoming_text},
        ]

    async def persist_turn(self, chat_id: int, user_text: str, assistant_text: str) -> None:
        """Persist conversation turn to storage backend."""
        _ = (chat_id, user_text, assistant_text)
