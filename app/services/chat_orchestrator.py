"""Chat message routing and business flow orchestration."""

from app.domain.state_machine import ChatMode, Event, next_mode
from app.services.ai_service import AIService
from app.services.handoff_service import HandoffService
from app.services.memory_service import MemoryService


class ChatOrchestrator:
    """Coordinates state, memory, AI response generation, and handoff."""

    def __init__(self, ai_service: AIService, memory_service: MemoryService, handoff_service: HandoffService):
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.handoff_service = handoff_service

    async def handle_user_message(self, chat_id: int, text: str, mode: ChatMode) -> tuple[ChatMode, str]:
        """Route a user message to AI or manager depending on current mode."""
        mode = next_mode(mode, Event.USER_MESSAGE)

        if mode == ChatMode.MANAGER_HANDOFF:
            await self.handoff_service.enqueue_for_manager(chat_id, text)
            return mode, "Forwarded to manager"

        if mode == ChatMode.CLOSED:
            return mode, "Chat is closed"

        context = await self.memory_service.build_context(chat_id, text)
        reply = await self.ai_service.generate_reply(context)
        await self.memory_service.persist_turn(chat_id, text, reply)

        return mode, reply
