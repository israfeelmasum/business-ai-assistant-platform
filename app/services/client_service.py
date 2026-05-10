"""
Business logic for client registration and management.
"""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.repositories.ai_provider_repository import AIProviderRepository
from app.schemas.client import ClientRegister
from app.core.security import generate_api_key, generate_api_secret, hash_secret
from app.core.exceptions import ClientNotFoundError, ProviderNotFoundError, InvalidAPIKeyError


class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client_repo = ClientRepository(db)
        self.provider_repo = AIProviderRepository(db)

    async def register(self, data: ClientRegister) -> tuple[Client, str]:
        """Register a new client. Returns client and plain api_secret (shown once)."""
        if data.provider_id:
            provider = await self.provider_repo.get_by_id(data.provider_id)
            if not provider:
                raise ProviderNotFoundError()

        api_key = generate_api_key()
        api_secret = generate_api_secret()

        client = Client(
            name=data.name,
            api_key=api_key,
            api_secret=hash_secret(api_secret),
            provider_id=data.provider_id,
            config=data.config,
            welcome_message=data.welcome_message,
        )

        created = await self.client_repo.create(client)
        return created, api_secret

    async def get_client(self, client_id: uuid.UUID) -> Client:
        client = await self.client_repo.get_by_id(client_id)
        if not client:
            raise ClientNotFoundError()
        return client

    async def authenticate(self, api_key: str) -> Client:
        """Authenticate a client by API key."""
        client = await self.client_repo.get_by_api_key(api_key)
        if not client:
            raise InvalidAPIKeyError()
        return client
