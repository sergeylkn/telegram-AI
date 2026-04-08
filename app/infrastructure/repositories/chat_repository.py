"""Repository for chat records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_chat_id(self, telegram_chat_id: int) -> Chat | None:
        result = await self.session.execute(select(Chat).where(Chat.telegram_chat_id == telegram_chat_id))
        return result.scalar_one_or_none()
