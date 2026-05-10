"""
Repository for AI Provider database operations.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_provider import AIProvider


class AIProviderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, provider: AIProvider) -> AIProvider:
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def get_by_id(self, provider_id: uuid.UUID) -> AIProvider | None:
        result = await self.db.execute(select(AIProvider).where(AIProvider.id == provider_id))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[AIProvider]:
        result = await self.db.execute(
            select(AIProvider).where(AIProvider.is_active == True).order_by(AIProvider.name)
        )
        return list(result.scalars().all())

    async def update(self, provider_id: uuid.UUID, **kwargs) -> AIProvider | None:
        await self.db.execute(
            update(AIProvider).where(AIProvider.id == provider_id).values(**kwargs)
        )
        return await self.get_by_id(provider_id)
