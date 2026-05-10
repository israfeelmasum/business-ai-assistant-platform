"""
Repository for Conversation database operations.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_by_session(self, client_id: uuid.UUID, session_id: str) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.client_id == client_id,
                Conversation.session_id == session_id,
                Conversation.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def update_messages(
        self, conversation_id: uuid.UUID, messages: list[dict], user_info: dict = None
    ) -> None:
        values = {"messages": messages}
        if user_info:
            values["user_info"] = user_info

        await self.db.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**values)
        )

    async def get_by_client(
        self, client_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.client_id == client_id, Conversation.is_active == True)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
