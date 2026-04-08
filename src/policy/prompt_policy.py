from __future__ import annotations

from src.models import ChatMetadata, ReplyConstraints


class PromptPolicy:
    """Prompt safety/tone policy for customer-facing replies."""

    @staticmethod
    def build_system_prompt(metadata: ChatMetadata, constraints: ReplyConstraints) -> str:
        mode_line = "You are a live manager assistant." if metadata.mode.value == "live_manager" else "You are a support assistant."
        uncertainty_line = (
            "If uncertain, say so clearly, avoid inventing facts, and ask a focused clarifying question."
            if constraints.forbid_speculation
            else "If uncertain, prefer concise assumptions and label them as assumptions."
        )
        policy_lines = [
            mode_line,
            "Tone: calm, professional, empathetic, and action-oriented.",
            "Do not claim to have completed real-world actions unless explicitly confirmed.",
            uncertainty_line,
        ]
        if constraints.mode_constraints:
            policy_lines.append("Mode constraints: " + "; ".join(constraints.mode_constraints))
        return "\n".join(policy_lines)
