from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import request

from src.models import PromptContext, ReplyConstraints
from src.services.ai_service import AIService


@dataclass(slots=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout_seconds: float = 20.0
    temperature: float = 0.2


class OllamaAIService(AIService):
    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    def generate_reply(self, context: PromptContext, constraints: ReplyConstraints) -> str:
        payload = {
            "model": self.config.model,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": constraints.max_tokens,
            },
            "messages": [{"role": "system", "content": context.system_prompt}, *context.messages],
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.config.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw.get("message", {}).get("content", "").strip()
