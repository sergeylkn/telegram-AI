"""Repository for event log records."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import EventLog


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, chat_id: int, event_type: str, payload: str = "") -> EventLog:
        event = EventLog(chat_id=chat_id, event_type=event_type, payload=payload)
        self.session.add(event)
        await self.session.flush()
        return event
