from __future__ import annotations

from src.models import ChatMetadata, Message, PromptContext, ReplyConstraints
from src.policy.prompt_policy import PromptPolicy
from src.services.summary_service import SummaryService


ROLE_MAP = {
    "user": "user",
    "assistant": "assistant",
    "manager": "assistant",
    "system": "system",
}


class MemoryService:
    def __init__(self, summary_service: SummaryService, recent_message_limit: int = 12) -> None:
        self.summary_service = summary_service
        self.recent_message_limit = recent_message_limit

    def build_context(
        self,
        chat_id: str,
        messages: list[Message],
        metadata: ChatMetadata,
        constraints: ReplyConstraints,
    ) -> PromptContext:
        snapshot = self.summary_service.maybe_update(chat_id=chat_id, messages=messages)
        recent = messages[-self.recent_message_limit :]
        mapped = [
            {
                "role": ROLE_MAP.get(m.role, "user"),
                "content": m.content,
            }
            for m in recent
            if m.content.strip()
        ]

        if snapshot.text:
            mapped.insert(0, {"role": "system", "content": snapshot.text})

        sys_prompt = PromptPolicy.build_system_prompt(metadata=metadata, constraints=constraints)
        meta = {
            "chat_id": metadata.chat_id,
            "customer_name": metadata.customer_name,
            "priority": metadata.priority,
            "mode": metadata.mode.value,
            "handoff_requested": metadata.handoff_requested,
            "handoff_active": metadata.handoff_active,
        }
        return PromptContext(system_prompt=sys_prompt, messages=mapped, metadata=meta)
