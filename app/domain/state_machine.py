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
