"""
Core sync service - handles create/update/delete from external systems.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_entity import AIEntity
from app.models.client import Client
from app.repositories.entity_type_repository import EntityTypeRepository
from app.repositories.ai_entity_repository import AIEntityRepository
from app.repositories.ai_knowledge_repository import AIKnowledgeRepository
from app.schemas.entity import EntitySyncRequest, EntitySyncResponse, SyncAction
from app.services.knowledge_service import KnowledgeService
from app.core.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__)


class EntitySyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.type_repo = EntityTypeRepository(db)
        self.entity_repo = AIEntityRepository(db)
        self.knowledge_repo = AIKnowledgeRepository(db)
        self.knowledge_service = KnowledgeService(db)

    async def sync(self, client: Client, request: EntitySyncRequest) -> EntitySyncResponse:
        """Main sync handler - routes to create/update/delete."""
        entity_type = await self.type_repo.get_or_create(client.id, request.entity_type)

        if request.action == SyncAction.CREATE:
            await self._handle_create(client, entity_type, request)
        elif request.action == SyncAction.UPDATE:
            await self._handle_update(client, entity_type, request)
        elif request.action == SyncAction.DELETE:
            await self._handle_delete(client, entity_type, request)

        return EntitySyncResponse(
            success=True,
            message=f"Entity {request.action.value}d successfully",
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            action=request.action,
        )

    async def _handle_create(self, client, entity_type, request: EntitySyncRequest):
        """Create entity + generate AI knowledge."""
        existing = await self.entity_repo.get_by_external_id(
            client.id, entity_type.id, request.entity_id
        )
        if existing:
            await self._handle_update(client, entity_type, request)
            return

        entity = AIEntity(
            client_id=client.id,
            entity_type_id=entity_type.id,
            external_id=request.entity_id,
            data=request.data,
        )
        created = await self.entity_repo.create(entity)

        await self.knowledge_service.generate_knowledge(
            client_id=client.id,
            entity_id=created.id,
            entity_type_id=entity_type.id,
            entity_type_name=entity_type.name,
            data=request.data,
        )

        logger.info(f"Created entity {request.entity_id} ({entity_type.name}) for client {client.id}")

    async def _handle_update(self, client, entity_type, request: EntitySyncRequest):
        """Update entity data + regenerate knowledge."""
        entity = await self.entity_repo.get_by_external_id(
            client.id, entity_type.id, request.entity_id
        )
        if not entity:
            raise EntityNotFoundError(request.entity_id)

        await self.entity_repo.update_data(entity.id, request.data)

        await self.knowledge_service.update_knowledge(
            entity_id=entity.id,
            entity_type_name=entity_type.name,
            data=request.data,
        )

        logger.info(f"Updated entity {request.entity_id} ({entity_type.name}) for client {client.id}")

    async def _handle_delete(self, client, entity_type, request: EntitySyncRequest):
        """Soft-delete entity + remove knowledge."""
        entity = await self.entity_repo.get_by_external_id(
            client.id, entity_type.id, request.entity_id
        )
        if not entity:
            raise EntityNotFoundError(request.entity_id)

        await self.knowledge_repo.delete_by_entity(entity.id)
        await self.entity_repo.soft_delete(entity.id)

        logger.info(f"Deleted entity {request.entity_id} ({entity_type.name}) for client {client.id}")
