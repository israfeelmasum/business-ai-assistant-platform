"""
AI Providers module — business logic.
Handles platform provider pool, BYOK per org, model listing.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_providers.crypto import encrypt_api_key, decrypt_api_key
from app.modules.ai_providers.models import (
    AiProvider, AiProviderModel, OrgAiProvider, ModelCapability
)
from app.modules.ai_providers.repository import (
    AiProviderRepository, AiProviderModelRepository, OrgAiProviderRepository
)
from app.modules.ai_providers.schemas import (
    AiProviderCreateRequest, AiProviderUpdateRequest, AiProviderResponse,
    AiProviderModelCreateRequest, AiProviderModelResponse,
    OrgAiProviderCreateRequest, OrgAiProviderUpdateRequest, OrgAiProviderResponse,
)
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)


class AiProviderService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.providers  = AiProviderRepository(db)
        self.models     = AiProviderModelRepository(db)
        self.org_keys   = OrgAiProviderRepository(db)
        self.members    = MemberRepository(db)

    # ── Platform Providers (super_admin) ───────────────────────────────────────

    async def list_providers(self, include_inactive: bool = False) -> List[AiProviderResponse]:
        providers = await self.providers.get_all(active_only=not include_inactive)
        return [AiProviderResponse.from_orm_with_key_flag(p) for p in providers]

    async def get_provider(self, provider_id: UUID) -> AiProviderResponse:
        p = await self.providers.get_by_id(provider_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        return AiProviderResponse.from_orm_with_key_flag(p)

    async def create_provider(self, req: AiProviderCreateRequest) -> AiProviderResponse:
        api_key_enc = encrypt_api_key(req.api_key) if req.api_key else None
        p = await self.providers.create(
            name=req.name,
            provider_type=req.provider_type,
            base_url=req.base_url,
            api_key_enc=api_key_enc,
            config=req.config,
            is_default=req.is_default,
        )
        await self.db.commit()
        await self.db.refresh(p)
        logger.info(f"Platform AI provider created: {p.name} ({p.provider_type})")
        return AiProviderResponse.from_orm_with_key_flag(p)

    async def update_provider(
        self, provider_id: UUID, req: AiProviderUpdateRequest
    ) -> AiProviderResponse:
        updates = req.model_dump(exclude_unset=True)
        if "api_key" in updates:
            updates["api_key_enc"] = encrypt_api_key(updates.pop("api_key")) if updates["api_key"] else None
        else:
            updates.pop("api_key", None)

        p = await self.providers.update(provider_id, **updates)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        await self.db.commit()
        return AiProviderResponse.from_orm_with_key_flag(p)

    async def deactivate_provider(self, provider_id: UUID) -> None:
        await self.providers.deactivate(provider_id)
        await self.db.commit()

    # ── Provider Models ────────────────────────────────────────────────────────

    async def list_models(
        self, provider_id: UUID, active_only: bool = True
    ) -> List[AiProviderModelResponse]:
        provider = await self.providers.get_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        models = await self.models.list_for_provider(provider_id, active_only)
        return [AiProviderModelResponse.model_validate(m) for m in models]

    async def add_model(
        self, provider_id: UUID, req: AiProviderModelCreateRequest
    ) -> AiProviderModelResponse:
        provider = await self.providers.get_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        m = await self.models.create(
            provider_id=provider_id,
            model_id=req.model_id,
            display_name=req.display_name,
            capability=req.capability,
            context_window=req.context_window,
            max_tokens=req.max_tokens,
            cost_input_per_1m=req.cost_input_per_1m,
            cost_output_per_1m=req.cost_output_per_1m,
            sort_order=req.sort_order,
        )
        await self.db.commit()
        await self.db.refresh(m)
        return AiProviderModelResponse.model_validate(m)

    async def deactivate_model(self, model_id: UUID) -> None:
        await self.models.deactivate(model_id)
        await self.db.commit()

    # ── BYOK Org Providers ─────────────────────────────────────────────────────

    async def list_org_providers(
        self, org_id: UUID, requester_id: UUID
    ) -> List[OrgAiProviderResponse]:
        await self._require_admin(org_id, requester_id)
        providers = await self.org_keys.list_org(org_id)
        return [OrgAiProviderResponse.from_orm_safe(p) for p in providers]

    async def add_org_provider(
        self, org_id: UUID, req: OrgAiProviderCreateRequest, requester_id: UUID
    ) -> OrgAiProviderResponse:
        await self._require_admin(org_id, requester_id)

        # Check BYOK feature flag on org's plan
        # (deferred — checked in chatbot config when BYOK is actually used)

        api_key_enc = encrypt_api_key(req.api_key)
        p = await self.org_keys.create(
            org_id=org_id,
            name=req.name,
            provider_type=req.provider_type,
            api_key_enc=api_key_enc,
            base_url=req.base_url,
            config=req.config,
        )
        await self.db.commit()
        await self.db.refresh(p)
        logger.info(f"BYOK provider added: {p.name} for org={org_id}")
        return OrgAiProviderResponse.from_orm_safe(p)

    async def update_org_provider(
        self, org_id: UUID, provider_id: UUID,
        req: OrgAiProviderUpdateRequest, requester_id: UUID
    ) -> OrgAiProviderResponse:
        await self._require_admin(org_id, requester_id)
        updates = req.model_dump(exclude_unset=True)
        if "api_key" in updates:
            updates["api_key_enc"] = encrypt_api_key(updates.pop("api_key")) if updates["api_key"] else None
        else:
            updates.pop("api_key", None)

        p = await self.org_keys.update(provider_id, org_id, **updates)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        await self.db.commit()
        return OrgAiProviderResponse.from_orm_safe(p)

    async def delete_org_provider(
        self, org_id: UUID, provider_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        p = await self.org_keys.get_by_id(provider_id, org_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Provider not found")
        await self.org_keys.delete(provider_id, org_id)
        await self.db.commit()

    # ── Provider Resolution (used by Chat Engine) ──────────────────────────────

    async def resolve_provider_key(
        self,
        org_id: UUID,
        capability: ModelCapability,
        org_provider_id: Optional[UUID] = None,
    ) -> dict:
        """
        Returns {provider_type, base_url, api_key, model_config} for a given capability.
        Priority: org BYOK > platform default > .env Ollama fallback.
        """
        # 1. Try org BYOK
        if org_provider_id:
            p = await self.org_keys.get_by_id(org_provider_id, org_id)
            if p and p.is_active:
                return {
                    "provider_type": p.provider_type,
                    "base_url": p.base_url,
                    "api_key": decrypt_api_key(p.api_key_enc),
                    "config": p.config,
                    "source": "byok",
                }

        # 2. Fallback to platform default from DB
        default = await self.providers.get_default(capability)
        if default:
            return {
                "provider_type": default.provider_type,
                "base_url": default.base_url,
                "api_key": decrypt_api_key(default.api_key_enc),
                "config": default.config,
                "source": "platform",
            }

        # 3. Final fallback — use .env Ollama config so chat always works
        import os
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_key = os.getenv("OLLAMA_API_KEY", "")
        logger.warning(f"No DB provider for {capability} — falling back to .env Ollama: {ollama_url}")
        return {
            "provider_type": "ollama",
            "base_url": ollama_url,
            "api_key": ollama_key,
            "config": {},
            "source": "env_fallback",
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _require_admin(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
        if member.role not in ("admin",):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admin role required")
