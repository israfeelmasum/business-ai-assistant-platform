"""
Repository for Sync Log database operations.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sync_log import SyncLog


class SyncLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, sync_log: SyncLog) -> SyncLog:
        self.db.add(sync_log)
        await self.db.flush()
        return sync_log

    async def update_log(self, log_id: uuid.UUID, **kwargs) -> None:
        await self.db.execute(
            update(SyncLog).where(SyncLog.id == log_id).values(**kwargs)
        )

    async def get_by_source(self, source_id: uuid.UUID, limit: int = 20) -> list[SyncLog]:
        result = await self.db.execute(
            select(SyncLog)
            .where(SyncLog.data_source_id == source_id)
            .order_by(SyncLog.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_by_source(self, source_id: uuid.UUID) -> SyncLog | None:
        result = await self.db.execute(
            select(SyncLog)
            .where(SyncLog.data_source_id == source_id)
            .order_by(SyncLog.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
