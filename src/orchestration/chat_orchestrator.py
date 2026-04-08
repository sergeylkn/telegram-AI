from __future__ import annotations

from src.models import ChatMetadata, Message, ReplyConstraints
from src.services.ai_service import AIService
from src.services.memory_service import MemoryService


class ChatOrchestrator:
    def __init__(self, memory_service: MemoryService, ai_service: AIService) -> None:
        self.memory_service = memory_service
        self.ai_service = ai_service

    def reply(
        self,
        chat_id: str,
        messages: list[Message],
        metadata: ChatMetadata,
        constraints: ReplyConstraints,
    ) -> str:
        self._enforce_business_logic(metadata, constraints)
        context = self.memory_service.build_context(
            chat_id=chat_id,
            messages=messages,
            metadata=metadata,
            constraints=constraints,
        )
        return self.ai_service.generate_reply(context=context, constraints=constraints)

    @staticmethod
    def _enforce_business_logic(metadata: ChatMetadata, constraints: ReplyConstraints) -> None:
        if metadata.handoff_active:
            raise RuntimeError("AI reply blocked: human handoff is currently active")

        if metadata.handoff_requested:
            raise RuntimeError("AI reply blocked: handoff requested and pending")

        if metadata.mode.value == "live_manager":
            guardrail = "Use live-manager tone with direct ownership and uncertainty transparency"
            if guardrail not in constraints.mode_constraints:
                constraints.mode_constraints.append(guardrail)
