"""Knowledge generation service."""
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_knowledge import AIKnowledge
from app.repositories.ai_knowledge_repository import AIKnowledgeRepository
from app.core.ai_client import ai_client

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.knowledge_repo = AIKnowledgeRepository(db)

    async def generate_knowledge(
        self, client_id: uuid.UUID, entity_id: uuid.UUID, entity_type_id: uuid.UUID, entity_type_name: str, data: dict,
    ) -> AIKnowledge:
        summary = await ai_client.generate_summary(entity_type_name, data)
        embedding = await ai_client.generate_embedding(summary)

        knowledge = AIKnowledge(
            client_id=client_id,
            entity_id=entity_id,
            entity_type_id=entity_type_id,
            summary=summary,
            embedding=embedding,
            meta_data={"entity_type": entity_type_name},
        )
        created = await self.knowledge_repo.create(knowledge)
        logger.info(f"Generated knowledge for entity {entity_id}")
        return created

    async def update_knowledge(self, entity_id: uuid.UUID, entity_type_name: str, data: dict) -> None:
        existing = await self.knowledge_repo.get_by_entity(entity_id)
        if not existing:
            return

        summary = await ai_client.generate_summary(entity_type_name, data)
        embedding = await ai_client.generate_embedding(summary)

        await self.knowledge_repo.update_knowledge(existing.id, summary, embedding)
        logger.info(f"Updated knowledge for entity {entity_id}")

    # 🚀 LAISA'S ADDITION: Added Delete functionality
    async def delete_knowledge(self, entity_id: uuid.UUID) -> None:
        existing = await self.knowledge_repo.get_by_entity(entity_id)
        if existing:
            await self.knowledge_repo.delete(existing.id)
            logger.info(f"Deleted knowledge for entity {entity_id}")