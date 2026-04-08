"""Redis-based deduplication helpers."""


class DedupeStore:
    """Tracks processed Telegram update IDs."""

    async def is_duplicate(self, update_id: int) -> bool:
        _ = update_id
        return False
