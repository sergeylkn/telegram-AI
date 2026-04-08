"""Repository for message records."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, chat_id: int, sender: str, text: str) -> Message:
        message = Message(chat_id=chat_id, sender=sender, text=text)
        self.session.add(message)
        await self.session.flush()
        return message
