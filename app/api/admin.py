"""Manager/operator control endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HandoffCommand(BaseModel):
    """Operator command to control chat handoff mode."""

    chat_id: int
    takeover_enabled: bool


@router.post("/handoff")
async def set_handoff(command: HandoffCommand) -> dict[str, str | int | bool]:
    """Set manager takeover status for a chat."""
    return {
        "chat_id": command.chat_id,
        "takeover_enabled": command.takeover_enabled,
        "status": "updated",
    }
