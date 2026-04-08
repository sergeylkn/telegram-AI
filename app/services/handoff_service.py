"""Manager takeover and release logic."""


class HandoffService:
    """Coordinates queueing and notifications for manager handoffs."""

    async def enqueue_for_manager(self, chat_id: int, message_text: str) -> None:
        """Queue a message for manager/operator intervention."""
        _ = (chat_id, message_text)

    async def set_takeover(self, chat_id: int, enabled: bool) -> None:
        """Enable or disable manager takeover for a chat."""
        _ = (chat_id, enabled)
