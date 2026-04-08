from __future__ import annotations

import unittest

from src.models import ChatMetadata, ChatMode, Message, ReplyConstraints
from src.orchestration.chat_orchestrator import ChatOrchestrator
from src.services.memory_service import MemoryService
from src.services.summary_service import InMemorySummaryStore, SummaryService, SummaryUpdatePolicy


class StubAI:
    def __init__(self) -> None:
        self.called = False

    def generate_reply(self, context, constraints):
        self.called = True
        return f"ok:{context.metadata['mode']}:{len(context.messages)}"


class OrchestratorTests(unittest.TestCase):
    def _build_orchestrator(self):
        summary_service = SummaryService(
            store=InMemorySummaryStore(),
            policy=SummaryUpdatePolicy(every_n_messages=2, max_context_chars=100),
        )
        memory = MemoryService(summary_service=summary_service, recent_message_limit=3)
        ai = StubAI()
        return ChatOrchestrator(memory_service=memory, ai_service=ai), ai

    def test_handoff_blocks_ai_invocation(self):
        orch, ai = self._build_orchestrator()
        meta = ChatMetadata(chat_id="c1", handoff_active=True)

        with self.assertRaises(RuntimeError):
            orch.reply("c1", [Message(role="user", content="hello")], meta, ReplyConstraints())

        self.assertFalse(ai.called)

    def test_live_manager_guardrail_is_injected(self):
        orch, _ = self._build_orchestrator()
        meta = ChatMetadata(chat_id="c1", mode=ChatMode.LIVE_MANAGER)
        constraints = ReplyConstraints(mode_constraints=[])

        result = orch.reply(
            "c1",
            [Message(role="user", content="need update"), Message(role="assistant", content="on it")],
            meta,
            constraints,
        )

        self.assertIn("ok:live_manager", result)
        self.assertTrue(any("live-manager tone" in c for c in constraints.mode_constraints))

    def test_summary_snapshot_is_injected(self):
        orch, _ = self._build_orchestrator()
        meta = ChatMetadata(chat_id="c1")
        constraints = ReplyConstraints()
        msgs = [
            Message(role="user", content="a" * 60),
            Message(role="assistant", content="b" * 60),
            Message(role="user", content="Status?"),
        ]

        result = orch.reply("c1", msgs, meta, constraints)
        self.assertIn("ok:live_manager", result)


if __name__ == "__main__":
    unittest.main()
