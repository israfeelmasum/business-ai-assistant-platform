"""
AI Provider management endpoints (admin).
"""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate, AIProviderResponse
from app.services.ai_provider_service import AIProviderService

router = APIRouter(prefix="/providers", tags=["AI Providers"])


@router.get("", response_model=list[AIProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List all active AI providers."""
    service = AIProviderService(db)
    return await service.list_active()


@router.post("", response_model=AIProviderResponse, status_code=201)
async def create_provider(
    data: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new AI provider."""
    service = AIProviderService(db)
    return await service.create(data)


@router.patch("/{provider_id}", response_model=AIProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    data: AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an AI provider's configuration."""
    service = AIProviderService(db)
    return await service.update(provider_id, data)
