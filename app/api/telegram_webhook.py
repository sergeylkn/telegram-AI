"""Telegram webhook intake endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TelegramWebhookPayload(BaseModel):
    """Subset of Telegram update payload required for routing."""

    update_id: int
    message: dict | None = None
    callback_query: dict | None = None


@router.post("/telegram")
async def receive_telegram_update(payload: TelegramWebhookPayload) -> dict[str, str]:
    """Accept Telegram webhook updates and enqueue for processing."""
    if payload.message is None and payload.callback_query is None:
        raise HTTPException(status_code=400, detail="Unsupported Telegram update")

    return {"status": "accepted"}
