"""
Repository for AI Knowledge - uses pgvector for semantic similarity search.
"""

import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_knowledge import AIKnowledge


class AIKnowledgeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, knowledge: AIKnowledge) -> AIKnowledge:
        self.db.add(knowledge)
        await self.db.flush()
        return knowledge

    async def get_by_entity(self, entity_id: uuid.UUID) -> AIKnowledge | None:
        result = await self.db.execute(
            select(AIKnowledge).where(AIKnowledge.entity_id == entity_id)
        )
        return result.scalar_one_or_none()

    async def update_knowledge(
        self, knowledge_id: uuid.UUID, summary: str, embedding: list[float]
    ) -> None:
        knowledge = await self.db.get(AIKnowledge, knowledge_id)
        if knowledge:
            knowledge.summary = summary
            knowledge.embedding = embedding
            await self.db.flush()

    async def delete_by_entity(self, entity_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(AIKnowledge).where(AIKnowledge.entity_id == entity_id)
        )

    async def search_similar(
        self,
        client_id: uuid.UUID,
        query_embedding: list[float],
        entity_type_id: uuid.UUID | None = None,
        limit: int = 5,
    ) -> list[AIKnowledge]:
        """Semantic search using pgvector cosine similarity."""
        query = (
            select(AIKnowledge)
            .where(AIKnowledge.client_id == client_id)
            .order_by(AIKnowledge.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        if entity_type_id:
            query = query.where(AIKnowledge.entity_type_id == entity_type_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())
