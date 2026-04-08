from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChatMode(str, Enum):
    LIVE_MANAGER = "live_manager"
    DEFAULT = "default"


@dataclass(slots=True)
class Message:
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class ChatMetadata:
    chat_id: str
    customer_name: str | None = None
    priority: str = "normal"
    mode: ChatMode = ChatMode.LIVE_MANAGER
    handoff_requested: bool = False
    handoff_active: bool = False


@dataclass(slots=True)
class ReplyConstraints:
    max_tokens: int = 500
    mode_constraints: list[str] = field(default_factory=list)
    forbid_speculation: bool = True


@dataclass(slots=True)
class PromptContext:
    system_prompt: str
    messages: list[dict[str, str]]
    metadata: dict[str, Any]
