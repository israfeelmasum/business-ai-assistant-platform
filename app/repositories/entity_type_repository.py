"""
Repository for Entity Type database operations.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entity_type import EntityType


class EntityTypeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, client_id: uuid.UUID, name: str) -> EntityType:
        """Get existing entity type or auto-create a new one during sync."""
        result = await self.db.execute(
            select(EntityType).where(
                EntityType.client_id == client_id,
                EntityType.name == name.lower().strip(),
            )
        )
        entity_type = result.scalar_one_or_none()

        if entity_type:
            return entity_type

        # Auto-create new entity type
        entity_type = EntityType(
            client_id=client_id,
            name=name.lower().strip(),
            display_name=name.strip().title() + "s",  # "course" -> "Courses"
        )
        self.db.add(entity_type)
        await self.db.flush()
        return entity_type

    async def get_by_client(self, client_id: uuid.UUID) -> list[EntityType]:
        """Get all active entity types for a client (for chat UI quick-select)."""
        result = await self.db.execute(
            select(EntityType).where(
                EntityType.client_id == client_id,
                EntityType.is_active == True,
            ).order_by(EntityType.name)
        )
        return list(result.scalars().all())

    async def get_by_name(self, client_id: uuid.UUID, name: str) -> EntityType | None:
        result = await self.db.execute(
            select(EntityType).where(
                EntityType.client_id == client_id,
                EntityType.name == name.lower().strip(),
            )
        )
        return result.scalar_one_or_none()
