"""
Repository for AI Entity database operations.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_entity import AIEntity


class AIEntityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, entity: AIEntity) -> AIEntity:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_external_id(
        self, client_id: uuid.UUID, entity_type_id: uuid.UUID, external_id: str
    ) -> AIEntity | None:
        result = await self.db.execute(
            select(AIEntity).where(
                AIEntity.client_id == client_id,
                AIEntity.entity_type_id == entity_type_id,
                AIEntity.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_data(self, entity_id: uuid.UUID, data: dict) -> AIEntity | None:
        await self.db.execute(
            update(AIEntity).where(AIEntity.id == entity_id).values(data=data)
        )
        result = await self.db.execute(select(AIEntity).where(AIEntity.id == entity_id))
        return result.scalar_one_or_none()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        await self.db.execute(
            update(AIEntity).where(AIEntity.id == entity_id).values(is_active=False)
        )
