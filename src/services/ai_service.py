from __future__ import annotations

from typing import Protocol

from src.models import PromptContext, ReplyConstraints


class AIService(Protocol):
    def generate_reply(self, context: PromptContext, constraints: ReplyConstraints) -> str:
        """Generate a reply for the given prompt context and constraints."""
