"""
Repository for Data Source database operations.
"""

import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.data_source import DataSource


class DataSourceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data_source: DataSource) -> DataSource:
        self.db.add(data_source)
        await self.db.flush()
        return data_source

    async def get_by_id(self, source_id: uuid.UUID) -> DataSource | None:
        result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client(self, client_id: uuid.UUID) -> list[DataSource]:
        result = await self.db.execute(
            select(DataSource)
            .where(DataSource.client_id == client_id)
            .order_by(DataSource.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_due_sources(self) -> list[DataSource]:
        """Get all active data sources that are due for sync."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(DataSource).where(
                DataSource.is_active == True,
            )
        )
        sources = list(result.scalars().all())
        # Filter in Python for interval logic (simpler than SQL interval arithmetic)
        due = []
        for s in sources:
            if s.last_synced_at is None:
                due.append(s)
            elif now - s.last_synced_at >= timedelta(minutes=s.sync_interval_minutes):
                due.append(s)
        return due

    async def update(self, source_id: uuid.UUID, **kwargs) -> DataSource | None:
        await self.db.execute(
            update(DataSource).where(DataSource.id == source_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(source_id)

    async def update_last_synced(self, source_id: uuid.UUID) -> None:
        await self.db.execute(
            update(DataSource)
            .where(DataSource.id == source_id)
            .values(last_synced_at=datetime.now(timezone.utc))
        )

    async def delete(self, source_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(DataSource).where(DataSource.id == source_id)
        )
