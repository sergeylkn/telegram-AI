from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ChatMode(str, Enum):
    AI_ACTIVE = "AI_ACTIVE"
    MANUAL_ACTIVE = "MANUAL_ACTIVE"
    RETURN_TO_AI = "RETURN_TO_AI"


class ChatEvent(str, Enum):
    USER_MESSAGE = "USER_MESSAGE"
    MANAGER_TAKEOVER = "MANAGER_TAKEOVER"
    MANAGER_FIRST_MESSAGE = "MANAGER_FIRST_MESSAGE"
    MANAGER_RELEASE = "MANAGER_RELEASE"
    ADMIN_MODE_SWITCH = "ADMIN_MODE_SWITCH"


@dataclass(frozen=True)
class ChatModeTransition:
    chat_id: str
    from_mode: ChatMode
    to_mode: ChatMode
    event: ChatEvent


class InvalidTransitionError(ValueError):
    """Raised when a transition is explicitly disallowed."""


class ChatStateMachine:
    """Per-chat mode state machine with auditable transition records."""

    def __init__(self) -> None:
        self._modes: Dict[str, ChatMode] = {}
        self._transition_log: List[ChatModeTransition] = []

    def mode_for(self, chat_id: str) -> ChatMode:
        """Returns current mode for a chat, defaulting to AI_ACTIVE."""
        return self._modes.setdefault(chat_id, ChatMode.AI_ACTIVE)

    @property
    def transition_log(self) -> List[ChatModeTransition]:
        return list(self._transition_log)

    def handle_event(
        self,
        chat_id: str,
        event: ChatEvent,
        *,
        target_mode: Optional[ChatMode] = None,
    ) -> ChatMode:
        current = self.mode_for(chat_id)
        next_mode = self._resolve_next_mode(current, event, target_mode=target_mode)

        if next_mode != current:
            self._modes[chat_id] = next_mode
            self._transition_log.append(
                ChatModeTransition(
                    chat_id=chat_id,
                    from_mode=current,
                    to_mode=next_mode,
                    event=event,
                )
            )

        return self.mode_for(chat_id)

    def _resolve_next_mode(
        self,
        current: ChatMode,
        event: ChatEvent,
        *,
        target_mode: Optional[ChatMode],
    ) -> ChatMode:
        if event == ChatEvent.ADMIN_MODE_SWITCH:
            if target_mode is None:
                raise InvalidTransitionError(
                    "ADMIN_MODE_SWITCH requires target_mode."
                )
            return target_mode

        if current == ChatMode.AI_ACTIVE:
            if event in (ChatEvent.MANAGER_TAKEOVER, ChatEvent.MANAGER_FIRST_MESSAGE):
                return ChatMode.MANUAL_ACTIVE
            if event in (ChatEvent.USER_MESSAGE, ChatEvent.MANAGER_RELEASE):
                return ChatMode.AI_ACTIVE

        if current == ChatMode.MANUAL_ACTIVE:
            if event in (
                ChatEvent.USER_MESSAGE,
                ChatEvent.MANAGER_TAKEOVER,
                ChatEvent.MANAGER_FIRST_MESSAGE,
            ):
                return ChatMode.MANUAL_ACTIVE
            if event == ChatEvent.MANAGER_RELEASE:
                return ChatMode.RETURN_TO_AI

        if current == ChatMode.RETURN_TO_AI:
            if event in (
                ChatEvent.USER_MESSAGE,
                ChatEvent.MANAGER_TAKEOVER,
                ChatEvent.MANAGER_FIRST_MESSAGE,
                ChatEvent.MANAGER_RELEASE,
            ):
                # Explicit switch required to return to AI_ACTIVE.
                return ChatMode.RETURN_TO_AI

        raise InvalidTransitionError(
            f"Invalid transition from {current} with event {event}."
        )
"""Deterministic chat mode transitions."""

from enum import Enum


class ChatMode(str, Enum):
    """Supported chat operating modes."""

    AI_ASSIST = "ai_assist"
    MANAGER_HANDOFF = "manager_handoff"
    CLOSED = "closed"


class Event(str, Enum):
    """Events that drive chat mode transitions."""

    USER_MESSAGE = "user_message"
    MANAGER_TAKEOVER = "manager_takeover"
    MANAGER_RELEASE = "manager_release"
    CLOSE_CHAT = "close_chat"


TRANSITIONS: dict[tuple[ChatMode, Event], ChatMode] = {
    (ChatMode.AI_ASSIST, Event.USER_MESSAGE): ChatMode.AI_ASSIST,
    (ChatMode.AI_ASSIST, Event.MANAGER_TAKEOVER): ChatMode.MANAGER_HANDOFF,
    (ChatMode.AI_ASSIST, Event.CLOSE_CHAT): ChatMode.CLOSED,
    (ChatMode.MANAGER_HANDOFF, Event.MANAGER_RELEASE): ChatMode.AI_ASSIST,
    (ChatMode.MANAGER_HANDOFF, Event.CLOSE_CHAT): ChatMode.CLOSED,
    (ChatMode.CLOSED, Event.MANAGER_RELEASE): ChatMode.AI_ASSIST,
}


def next_mode(current_mode: ChatMode, event: Event) -> ChatMode:
    """Return the next mode for a given event; keep state if unmapped."""
    return TRANSITIONS.get((current_mode, event), current_mode)
