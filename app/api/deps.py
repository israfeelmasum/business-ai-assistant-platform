"""Dependency injection - auth, database session."""
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.client import Client
from app.services.client_service import ClientService
from app.core.exceptions import InvalidAPIKeyError

# This single line adds the "Authorize" button to Swagger UI!
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def get_current_client(
    x_api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Client:
    """Authenticate client via X-API-Key header."""
    if not x_api_key:
        raise InvalidAPIKeyError()
    service = ClientService(db)
    return await service.authenticate(x_api_key)