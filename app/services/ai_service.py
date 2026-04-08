"""LLM abstraction with an Ollama adapter implementation."""

from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class AIService:
    """Generates assistant responses via Ollama chat API."""

    base_url: str
    model: str
    timeout_seconds: float = 30.0

    async def generate_reply(self, context: list[dict[str, str]]) -> str:
        """Generate a response from the configured LLM provider."""
        payload = {"model": self.model, "messages": context, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        return data.get("message", {}).get("content", "")
