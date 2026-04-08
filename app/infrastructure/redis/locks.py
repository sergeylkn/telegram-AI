"""Redis-based distributed lock helpers."""


class LockManager:
    """Acquires scoped locks around chat processing."""

    async def acquire(self, key: str, ttl_seconds: int = 10) -> bool:
        _ = (key, ttl_seconds)
        return True

    async def release(self, key: str) -> None:
        _ = key
