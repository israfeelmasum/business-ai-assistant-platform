"""
API routes for Data Source management and auto-sync operations.
"""

import uuid
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.client import Client
from app.api.deps import get_current_client
from app.services.data_source_service import DataSourceService
from app.services.auto_sync_service import AutoSyncService
from app.repositories.sync_log_repository import SyncLogRepository
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    SyncLogResponse,
    ManualSyncResponse,
    TestConnectionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


@router.post("", response_model=DataSourceResponse)
async def create_data_source(
    request: DataSourceCreate,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Register a new external API data source for auto-sync."""
    service = DataSourceService(db)
    source = await service.create_source(client, request.model_dump())
    return source


@router.get("", response_model=list[DataSourceResponse])
async def list_data_sources(
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """List all data sources for the authenticated client."""
    service = DataSourceService(db)
    return await service.list_sources(client)


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_data_source(
    source_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific data source."""
    service = DataSourceService(db)
    return await service.get_source(client, source_id)


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: uuid.UUID,
    request: DataSourceUpdate,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Update data source configuration."""
    service = DataSourceService(db)
    return await service.update_source(client, source_id, request.model_dump(exclude_unset=True))


@router.delete("/{source_id}")
async def delete_data_source(
    source_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Delete a data source and stop its sync schedule."""
    service = DataSourceService(db)
    await service.delete_source(client, source_id)
    return {"success": True, "message": "Data source deleted"}


@router.post("/{source_id}/sync", response_model=ManualSyncResponse)
async def trigger_manual_sync(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate sync for a data source."""
    ds_service = DataSourceService(db)
    source = await ds_service.get_source(client, source_id)

    sync_service = AutoSyncService(db)
    sync_log = await sync_service.execute_sync(source)

    return ManualSyncResponse(
        success=True,
        message=f"Sync completed: {sync_log.status}",
        sync_log_id=sync_log.id,
    )


@router.get("/{source_id}/logs", response_model=list[SyncLogResponse])
async def get_sync_logs(
    source_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get sync history for a data source."""
    ds_service = DataSourceService(db)
    await ds_service.get_source(client, source_id)  # Verify ownership

    log_repo = SyncLogRepository(db)
    return await log_repo.get_by_source(source_id)


@router.post("/{source_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    source_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Test connection to external API. Fetches first page only, does NOT sync."""
    ds_service = DataSourceService(db)
    source = await ds_service.get_source(client, source_id)

    sync_service = AutoSyncService(db)
    result = await sync_service.test_connection(source)
    return TestConnectionResponse(**result)
