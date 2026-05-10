"""
AI Providers router — platform providers (super_admin) + BYOK per org (admin).
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.ai_providers.schemas import (
    AiProviderCreateRequest, AiProviderUpdateRequest, AiProviderResponse,
    AiProviderModelCreateRequest, AiProviderModelResponse,
    OrgAiProviderCreateRequest, OrgAiProviderUpdateRequest, OrgAiProviderResponse,
)
from app.modules.ai_providers.service import AiProviderService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Providers"])


# ── Platform Provider Pool (super_admin only) ──────────────────────────────────

@router.get("/ai-providers", response_model=List[AiProviderResponse],
            dependencies=[Depends(require_role(UserRole.super_admin))])
async def list_ai_providers(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List all platform AI providers. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.list_providers(include_inactive=include_inactive)


@router.post("/ai-providers", response_model=AiProviderResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role(UserRole.super_admin))])
async def create_ai_provider(
    req: AiProviderCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a platform AI provider. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.create_provider(req)


@router.get("/ai-providers/{provider_id}", response_model=AiProviderResponse,
            dependencies=[Depends(require_role(UserRole.super_admin))])
async def get_ai_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get provider details. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.get_provider(provider_id)


@router.patch("/ai-providers/{provider_id}", response_model=AiProviderResponse,
              dependencies=[Depends(require_role(UserRole.super_admin))])
async def update_ai_provider(
    provider_id: UUID,
    req: AiProviderUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a platform AI provider. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.update_provider(provider_id, req)


@router.delete("/ai-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role(UserRole.super_admin))])
async def deactivate_ai_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a platform AI provider. Super-admin only."""
    svc = AiProviderService(db)
    await svc.deactivate_provider(provider_id)


# ── Provider Models ────────────────────────────────────────────────────────────

@router.get("/ai-providers/{provider_id}/models",
            response_model=List[AiProviderModelResponse],
            dependencies=[Depends(require_role(UserRole.super_admin))])
async def list_provider_models(
    provider_id: UUID,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List models for a provider. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.list_models(provider_id, active_only=active_only)


@router.post("/ai-providers/{provider_id}/models",
             response_model=AiProviderModelResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role(UserRole.super_admin))])
async def add_provider_model(
    provider_id: UUID,
    req: AiProviderModelCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a model to a provider. Super-admin only."""
    svc = AiProviderService(db)
    return await svc.add_model(provider_id, req)


@router.delete("/ai-providers/models/{model_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role(UserRole.super_admin))])
async def deactivate_provider_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a provider model. Super-admin only."""
    svc = AiProviderService(db)
    await svc.deactivate_model(model_id)


# ── BYOK Org Providers ─────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/ai-providers",
            response_model=List[OrgAiProviderResponse])
async def list_org_ai_providers(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List BYOK AI providers for an organization. Admin only."""
    svc = AiProviderService(db)
    return await svc.list_org_providers(org_id, requester_id=current_user.id)


@router.post("/organizations/{org_id}/ai-providers",
             response_model=OrgAiProviderResponse,
             status_code=status.HTTP_201_CREATED)
async def add_org_ai_provider(
    org_id: UUID,
    req: OrgAiProviderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a BYOK AI provider (bring your own API key). Admin only."""
    svc = AiProviderService(db)
    return await svc.add_org_provider(org_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/ai-providers/{provider_id}",
              response_model=OrgAiProviderResponse)
async def update_org_ai_provider(
    org_id: UUID,
    provider_id: UUID,
    req: OrgAiProviderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a BYOK provider. Admin only."""
    svc = AiProviderService(db)
    return await svc.update_org_provider(org_id, provider_id, req,
                                         requester_id=current_user.id)


@router.delete("/organizations/{org_id}/ai-providers/{provider_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_ai_provider(
    org_id: UUID,
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a BYOK provider. Admin only."""
    svc = AiProviderService(db)
    await svc.delete_org_provider(org_id, provider_id, requester_id=current_user.id)
