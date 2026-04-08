"""Repository for chat mode updates."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Chat


class ModeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_mode(self, chat: Chat, mode: str) -> Chat:
        chat.mode = mode
        await self.session.flush()
        return chat
