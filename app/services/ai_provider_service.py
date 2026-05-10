"""
Business logic for AI provider management.
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_provider import AIProvider
from app.repositories.ai_provider_repository import AIProviderRepository
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate
from app.core.exceptions import ProviderNotFoundError


class AIProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIProviderRepository(db)

    async def create(self, data: AIProviderCreate) -> AIProvider:
        provider = AIProvider(
            name=data.name,
            model_name=data.model_name,
            provider_type=data.provider_type,
            config=data.config,
        )
        return await self.repo.create(provider)

    async def list_active(self) -> list[AIProvider]:
        return await self.repo.list_active()

    async def update(self, provider_id: uuid.UUID, data: AIProviderUpdate) -> AIProvider:
        provider = await self.repo.get_by_id(provider_id)
        if not provider:
            raise ProviderNotFoundError()

        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(provider_id, **update_data)
