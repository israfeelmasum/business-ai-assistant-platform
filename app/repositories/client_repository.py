"""
Repository for Client database operations.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client


class ClientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, client: Client) -> Client:
        self.db.add(client)
        await self.db.flush()
        return client

    async def get_by_id(self, client_id: uuid.UUID) -> Client | None:
        result = await self.db.execute(select(Client).where(Client.id == client_id))
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> Client | None:
        result = await self.db.execute(
            select(Client).where(Client.api_key == api_key, Client.is_active == True)
        )
        return result.scalar_one_or_none()

    async def update(self, client_id: uuid.UUID, **kwargs) -> Client | None:
        await self.db.execute(
            update(Client).where(Client.id == client_id).values(**kwargs)
        )
        return await self.get_by_id(client_id)

    async def list_all(self) -> list[Client]:
        result = await self.db.execute(select(Client).order_by(Client.created_at.desc()))
        return list(result.scalars().all())
