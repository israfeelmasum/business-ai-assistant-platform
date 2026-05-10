"""
AI Providers module — repository layer.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai_providers.models import (
    AiProvider, AiProviderModel, OrgAiProvider,
    ProviderType, ModelCapability
)


class AiProviderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, active_only: bool = True) -> List[AiProvider]:
        q = select(AiProvider).options(selectinload(AiProvider.models))
        if active_only:
            q = q.where(AiProvider.is_active == True)
        q = q.order_by(AiProvider.is_default.desc(), AiProvider.name)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, provider_id: UUID) -> Optional[AiProvider]:
        result = await self.db.execute(
            select(AiProvider)
            .where(AiProvider.id == provider_id)
            .options(selectinload(AiProvider.models))
        )
        return result.scalar_one_or_none()

    async def get_default(self, capability: ModelCapability) -> Optional[AiProvider]:
        """Get default platform provider that supports a given capability."""
        result = await self.db.execute(
            select(AiProvider)
            .join(AiProviderModel, AiProvider.id == AiProviderModel.provider_id)
            .where(
                AiProvider.is_active == True,
                AiProvider.is_default == True,
                AiProviderModel.capability == capability,
                AiProviderModel.is_active == True,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self, name: str, provider_type: ProviderType,
        base_url: Optional[str] = None,
        api_key_enc: Optional[str] = None,
        config: Optional[dict] = None,
        is_default: bool = False,
    ) -> AiProvider:
        provider = AiProvider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_enc=api_key_enc,
            config=config or {},
            is_default=is_default,
        )
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def update(self, provider_id: UUID, **kwargs) -> Optional[AiProvider]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(AiProvider).where(AiProvider.id == provider_id).values(**kwargs)
        )
        return await self.get_by_id(provider_id)

    async def deactivate(self, provider_id: UUID) -> None:
        await self.db.execute(
            update(AiProvider)
            .where(AiProvider.id == provider_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )


class AiProviderModelRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_provider(self, provider_id: UUID, active_only: bool = True) -> List[AiProviderModel]:
        q = select(AiProviderModel).where(AiProviderModel.provider_id == provider_id)
        if active_only:
            q = q.where(AiProviderModel.is_active == True)
        q = q.order_by(AiProviderModel.sort_order, AiProviderModel.model_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, model_id: UUID) -> Optional[AiProviderModel]:
        result = await self.db.execute(
            select(AiProviderModel).where(AiProviderModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, provider_id: UUID, model_id: str, display_name: str,
        capability: ModelCapability, context_window: Optional[int] = None,
        max_tokens: Optional[int] = None, cost_input_per_1m=0,
        cost_output_per_1m=0, sort_order: int = 0,
    ) -> AiProviderModel:
        m = AiProviderModel(
            provider_id=provider_id,
            model_id=model_id,
            display_name=display_name,
            capability=capability,
            context_window=context_window,
            max_tokens=max_tokens,
            cost_input_per_1m=cost_input_per_1m,
            cost_output_per_1m=cost_output_per_1m,
            sort_order=sort_order,
        )
        self.db.add(m)
        await self.db.flush()
        return m

    async def deactivate(self, model_id: UUID) -> None:
        await self.db.execute(
            update(AiProviderModel)
            .where(AiProviderModel.id == model_id)
            .values(is_active=False)
        )


class OrgAiProviderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_org(self, org_id: UUID, active_only: bool = False) -> List[OrgAiProvider]:
        q = select(OrgAiProvider).where(OrgAiProvider.org_id == org_id)
        if active_only:
            q = q.where(OrgAiProvider.is_active == True)
        q = q.order_by(OrgAiProvider.name)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, provider_id: UUID, org_id: UUID) -> Optional[OrgAiProvider]:
        result = await self.db.execute(
            select(OrgAiProvider).where(
                OrgAiProvider.id == provider_id,
                OrgAiProvider.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, org_id: UUID, name: str, provider_type: ProviderType,
        api_key_enc: str, base_url: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> OrgAiProvider:
        p = OrgAiProvider(
            org_id=org_id,
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_enc=api_key_enc,
            config=config or {},
        )
        self.db.add(p)
        await self.db.flush()
        return p

    async def update(self, provider_id: UUID, org_id: UUID, **kwargs) -> Optional[OrgAiProvider]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(OrgAiProvider)
            .where(OrgAiProvider.id == provider_id, OrgAiProvider.org_id == org_id)
            .values(**kwargs)
        )
        return await self.get_by_id(provider_id, org_id)

    async def delete(self, provider_id: UUID, org_id: UUID) -> None:
        from sqlalchemy import delete
        await self.db.execute(
            delete(OrgAiProvider).where(
                OrgAiProvider.id == provider_id,
                OrgAiProvider.org_id == org_id,
            )
        )
