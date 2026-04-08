"""Telegram Bot API client adapter."""

import httpx


class TelegramClient:
    """Minimal Telegram Bot API wrapper for outbound messaging."""

    def __init__(self, bot_token: str, base_url: str = "https://api.telegram.org"):
        self.base_url = f"{base_url}/bot{bot_token}"

    async def send_message(self, chat_id: int, text: str) -> dict:
        """Send a text message to a Telegram chat."""
        payload = {"chat_id": chat_id, "text": text}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
            return response.json()
