"""Minimal Telegram AI handoff state engine used by tests and as app entrypoint."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Mode(str, Enum):
    AI = "ai"
    MANUAL = "manual"


@dataclass
class ChatState:
    mode: Mode = Mode.AI
    manager_id: Optional[int] = None
    summary: Optional[str] = None
    messages: List[dict] = field(default_factory=list)


class ChatStateStore:
    """In-memory state store that models handoff rules per chat."""

    def __init__(self) -> None:
        self._states: Dict[int, ChatState] = {}

    def get(self, chat_id: int) -> ChatState:
        if chat_id not in self._states:
            self._states[chat_id] = ChatState()
        return self._states[chat_id]

    def manager_takeover(self, chat_id: int, manager_id: int) -> None:
        state = self.get(chat_id)
        state.mode = Mode.MANUAL
        state.manager_id = manager_id

    def switch_to_ai(self, chat_id: int) -> None:
        state = self.get(chat_id)
        state.mode = Mode.AI

    def ingest_message(
        self,
        chat_id: int,
        sender_role: str,
        text: str,
        sender_id: Optional[int] = None,
        from_manager: bool = False,
    ) -> bool:
        """Store message and return whether AI should be triggered.

        Rules:
        - New chats are in AI mode by default.
        - First manager message causes takeover (manual mode).
        - In manual mode, user messages do not trigger AI.
        - In AI mode, user messages trigger AI.
        """

        state = self.get(chat_id)

        if from_manager:
            # First manager message disables AI automatically.
            if state.mode == Mode.AI:
                state.mode = Mode.MANUAL
            if sender_id is not None:
                state.manager_id = sender_id

        state.messages.append({"role": sender_role, "text": text})

        return sender_role == "user" and state.mode == Mode.AI


def assemble_context(
    state: ChatState,
    *,
    recent_window: int = 6,
    include_summary: bool = True,
) -> List[dict]:
    """Build prompt context from summary + recent rolling window."""

    context: List[dict] = []
    if include_summary and state.summary:
        context.append({"role": "system", "text": f"Summary: {state.summary}"})

    if recent_window <= 0:
        return context

    context.extend(state.messages[-recent_window:])
    return context


if __name__ == "__main__":
    print("telegram-AI app container is healthy")
