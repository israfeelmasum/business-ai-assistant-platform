"""
Client registration and management endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.client import Client
from app.api.deps import get_current_client
from app.schemas.client import ClientRegister, ClientResponse, ClientRegisteredResponse
from app.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["Clients"])

# ==========================================
# Schema for Admin Dashboard Updates
# ==========================================
class ClientUpdateParams(BaseModel):
    name: Optional[str] = None
    welcome_message: Optional[str] = None


@router.post("/register", response_model=ClientRegisteredResponse, status_code=201)
async def register_client(
    data: ClientRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new external system. Returns api_key and api_secret (secret shown once)."""
    service = ClientService(db)
    client, api_secret = await service.register(data)

    return ClientRegisteredResponse(
        id=client.id,
        name=client.name,
        api_key=client.api_key,
        api_secret=api_secret,
    )


@router.get("/me", response_model=ClientResponse)
async def get_my_profile(
    client: Client = Depends(get_current_client),
):
    """Get current client's profile (authenticated via X-API-Key header)."""
    return client


# ==========================================
# 🚀 LAISA'S UPGRADE: Client Edit Route
# ==========================================
@router.patch("/me", response_model=ClientResponse)
async def update_my_profile(
    update_data: ClientUpdateParams,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Update current client's profile from the SaaS Dashboard."""
    if update_data.name:
        client.name = update_data.name
    if update_data.welcome_message is not None:
        client.welcome_message = update_data.welcome_message
        
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client