from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.models import Message


@dataclass(slots=True)
class SummarySnapshot:
    text: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)
    source_message_count: int = 0


class SummaryStore:
    def get(self, chat_id: str) -> SummarySnapshot:
        raise NotImplementedError

    def put(self, chat_id: str, snapshot: SummarySnapshot) -> None:
        raise NotImplementedError


class InMemorySummaryStore(SummaryStore):
    def __init__(self) -> None:
        self._snapshots: dict[str, SummarySnapshot] = {}

    def get(self, chat_id: str) -> SummarySnapshot:
        return self._snapshots.get(chat_id, SummarySnapshot())

    def put(self, chat_id: str, snapshot: SummarySnapshot) -> None:
        self._snapshots[chat_id] = snapshot


@dataclass(slots=True)
class SummaryUpdatePolicy:
    every_n_messages: int = 8
    max_context_chars: int = 4500
    refresh_interval: timedelta = timedelta(minutes=10)


class SummaryService:
    def __init__(self, store: SummaryStore, policy: SummaryUpdatePolicy | None = None) -> None:
        self.store = store
        self.policy = policy or SummaryUpdatePolicy()

    def maybe_update(self, chat_id: str, messages: list[Message]) -> SummarySnapshot:
        prior = self.store.get(chat_id)
        if not self._should_update(prior, messages):
            return prior

        latest_window = messages[-30:]
        bullets = [f"- {m.role}: {m.content.strip()}" for m in latest_window if m.content.strip()]
        summary_text = "Conversation summary:\n" + "\n".join(bullets[:20])
        snapshot = SummarySnapshot(
            text=summary_text,
            updated_at=datetime.utcnow(),
            source_message_count=len(messages),
        )
        self.store.put(chat_id, snapshot)
        return snapshot

    def _should_update(self, prior: SummarySnapshot, messages: list[Message]) -> bool:
        if not messages:
            return False
        msg_delta = len(messages) - prior.source_message_count
        if msg_delta >= self.policy.every_n_messages:
            return True

        char_count = sum(len(m.content) for m in messages)
        if char_count > self.policy.max_context_chars:
            return True

        return datetime.utcnow() - prior.updated_at >= self.policy.refresh_interval
