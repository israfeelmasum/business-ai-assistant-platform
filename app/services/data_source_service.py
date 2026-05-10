"""
Data Source Service - CRUD operations for data source configurations.
"""

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.data_source import DataSource
from app.models.client import Client
from app.repositories.data_source_repository import DataSourceRepository
from app.core.exceptions import DataSourceNotFoundError

logger = logging.getLogger(__name__)


class DataSourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DataSourceRepository(db)

    async def create_source(self, client: Client, data: dict) -> DataSource:
        source = DataSource(client_id=client.id, **data)
        created = await self.repo.create(source)
        await self.db.commit()
        logger.info(f"Created data source '{data['name']}' for client {client.id}")
        return created

    async def list_sources(self, client: Client) -> list[DataSource]:
        return await self.repo.get_by_client(client.id)

    async def get_source(self, client: Client, source_id: uuid.UUID) -> DataSource:
        source = await self.repo.get_by_id(source_id)
        if not source or source.client_id != client.id:
            raise DataSourceNotFoundError(str(source_id))
        return source

    async def update_source(self, client: Client, source_id: uuid.UUID, data: dict) -> DataSource:
        source = await self.get_source(client, source_id)
        # Filter out None values
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            return source
        updated = await self.repo.update(source_id, **update_data)
        await self.db.commit()
        logger.info(f"Updated data source '{source.name}' for client {client.id}")
        return updated

    async def delete_source(self, client: Client, source_id: uuid.UUID) -> None:
        await self.get_source(client, source_id)  # Verify ownership
        await self.repo.delete(source_id)
        await self.db.commit()
        logger.info(f"Deleted data source {source_id} for client {client.id}")
