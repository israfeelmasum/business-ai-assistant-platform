"""
Knowledge Base module — repository layer.
Includes vector similarity search via pgvector.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeBase, KnowledgeSource, KnowledgeDocument, KnowledgeChunk,
    KnowledgeQAPair, KnowledgeSyncLog, DocumentStatus, VECTOR_AVAILABLE
)


class KBRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, chatbot_id: UUID, org_id: UUID, name: str,
                     description: Optional[str] = None) -> KnowledgeBase:
        kb = KnowledgeBase(chatbot_id=chatbot_id, org_id=org_id,
                           name=name, description=description)
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def get_by_id(self, kb_id: UUID, org_id: Optional[UUID] = None) -> Optional[KnowledgeBase]:
        q = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        if org_id:
            q = q.where(KnowledgeBase.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_chatbot(self, chatbot_id: UUID) -> List[KnowledgeBase]:
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.chatbot_id == chatbot_id)
            .order_by(KnowledgeBase.name)
        )
        return list(result.scalars().all())

    async def update(self, kb_id: UUID, org_id: UUID, **kwargs) -> Optional[KnowledgeBase]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id)
            .values(**kwargs)
        )
        return await self.get_by_id(kb_id, org_id)

    async def delete(self, kb_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id
            )
        )


class SourceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, kb_id: UUID, org_id: UUID, **kwargs) -> KnowledgeSource:
        src = KnowledgeSource(knowledge_base_id=kb_id, org_id=org_id, **kwargs)
        self.db.add(src)
        await self.db.flush()
        return src

    async def get_by_id(self, source_id: UUID, org_id: Optional[UUID] = None) -> Optional[KnowledgeSource]:
        q = select(KnowledgeSource).where(KnowledgeSource.id == source_id)
        if org_id:
            q = q.where(KnowledgeSource.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_kb(self, kb_id: UUID) -> List[KnowledgeSource]:
        result = await self.db.execute(
            select(KnowledgeSource)
            .where(KnowledgeSource.knowledge_base_id == kb_id)
            .order_by(KnowledgeSource.name)
        )
        return list(result.scalars().all())

    async def get_active_due(self) -> List[KnowledgeSource]:
        """Sources that are due for sync (next_sync_at <= NOW())."""
        result = await self.db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.is_active == True,
                KnowledgeSource.next_sync_at <= datetime.now(timezone.utc),
            )
        )
        return list(result.scalars().all())

    async def update(self, source_id: UUID, **kwargs) -> Optional[KnowledgeSource]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == source_id).values(**kwargs)
        )
        return await self.get_by_id(source_id)

    async def delete(self, source_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeSource).where(
                KnowledgeSource.id == source_id, KnowledgeSource.org_id == org_id
            )
        )


class DocumentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, kb_id: UUID, org_id: UUID, **kwargs) -> KnowledgeDocument:
        doc = KnowledgeDocument(knowledge_base_id=kb_id, org_id=org_id, **kwargs)
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_by_id(self, doc_id: UUID) -> Optional[KnowledgeDocument]:
        result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, kb_id: UUID, content_hash: str) -> Optional[KnowledgeDocument]:
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.content_hash == content_hash,
            )
        )
        return result.scalar_one_or_none()

    async def list_kb(self, kb_id: UUID, status: Optional[DocumentStatus] = None,
                      limit: int = 50, offset: int = 0) -> List[KnowledgeDocument]:
        q = select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
        if status:
            q = q.where(KnowledgeDocument.status == status)
        q = q.order_by(KnowledgeDocument.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update_status(self, doc_id: UUID, status: DocumentStatus,
                            error_message: Optional[str] = None,
                            chunk_count: Optional[int] = None) -> None:
        vals = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if error_message is not None:
            vals["error_message"] = error_message
        if chunk_count is not None:
            vals["chunk_count"] = chunk_count
        await self.db.execute(
            update(KnowledgeDocument).where(KnowledgeDocument.id == doc_id).values(**vals)
        )

    async def delete(self, doc_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeDocument).where(
                KnowledgeDocument.id == doc_id, KnowledgeDocument.org_id == org_id
            )
        )


class ChunkRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(self, chunks: List[KnowledgeChunk]) -> None:
        for chunk in chunks:
            self.db.add(chunk)
        await self.db.flush()

    async def delete_for_document(self, doc_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id)
        )

    async def vector_search(
        self,
        kb_id: UUID,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """HNSW cosine similarity search against knowledge_chunks."""
        if not VECTOR_AVAILABLE:
            return []

        # pgvector cosine distance (1 - cosine_similarity)
        # We want similarity >= threshold, so distance <= (1 - threshold)
        max_distance = 1.0 - threshold
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT id, content, chunk_index, token_count, metadata,
                   document_id, knowledge_base_id, created_at,
                   (1 - (embedding <=> CAST(:embedding AS vector))) AS score
            FROM knowledge_chunks
            WHERE knowledge_base_id = :kb_id
              AND embedding IS NOT NULL
              AND (1 - (embedding <=> CAST(:embedding AS vector))) >= :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = await self.db.execute(sql, {
            "embedding": embedding_str,
            "kb_id": str(kb_id),
            "threshold": threshold,
            "top_k": top_k,
        })
        rows = result.mappings().all()

        chunks_with_scores = []
        for row in rows:
            chunk = KnowledgeChunk(
                id=row["id"],
                document_id=row["document_id"],
                knowledge_base_id=row["knowledge_base_id"],
                content=row["content"],
                chunk_index=row["chunk_index"],
                token_count=row["token_count"],
                metadata=row["metadata"] or {},
                created_at=row["created_at"],
            )
            chunks_with_scores.append((chunk, float(row["score"])))

        return chunks_with_scores


class QAPairRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, kb_id: UUID, org_id: UUID, question: str,
                     answer: str, created_by: UUID,
                     tags: Optional[List[str]] = None,
                     category: Optional[str] = None,
                     sort_order: int = 0,
                     embedding: Optional[List[float]] = None) -> KnowledgeQAPair:
        qa = KnowledgeQAPair(
            knowledge_base_id=kb_id, org_id=org_id,
            question=question, answer=answer,
            created_by=created_by, tags=tags or [],
            category=category, sort_order=sort_order,
        )
        if embedding and VECTOR_AVAILABLE:
            qa.embedding = embedding
        self.db.add(qa)
        await self.db.flush()
        return qa

    async def get_by_id(self, qa_id: UUID, org_id: Optional[UUID] = None) -> Optional[KnowledgeQAPair]:
        q = select(KnowledgeQAPair).where(KnowledgeQAPair.id == qa_id)
        if org_id:
            q = q.where(KnowledgeQAPair.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_kb(self, kb_id: UUID, active_only: bool = True,
                      category: Optional[str] = None,
                      limit: int = 200, offset: int = 0) -> List[KnowledgeQAPair]:
        q = select(KnowledgeQAPair).where(KnowledgeQAPair.knowledge_base_id == kb_id)
        if active_only:
            q = q.where(KnowledgeQAPair.is_active == True)
        if category:
            q = q.where(KnowledgeQAPair.category == category)
        q = q.order_by(KnowledgeQAPair.sort_order.asc(), KnowledgeQAPair.created_at.asc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def bulk_reorder(self, items: List[dict], org_id: UUID) -> None:
        """Bulk update sort_order for multiple QA pairs."""
        for item in items:
            await self.db.execute(
                update(KnowledgeQAPair)
                .where(KnowledgeQAPair.id == item["id"], KnowledgeQAPair.org_id == org_id)
                .values(sort_order=item["sort_order"], updated_at=datetime.now(timezone.utc))
            )

    async def update(self, qa_id: UUID, org_id: UUID, **kwargs) -> Optional[KnowledgeQAPair]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(KnowledgeQAPair)
            .where(KnowledgeQAPair.id == qa_id, KnowledgeQAPair.org_id == org_id)
            .values(**kwargs)
        )
        return await self.get_by_id(qa_id, org_id)

    async def delete(self, qa_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeQAPair).where(
                KnowledgeQAPair.id == qa_id, KnowledgeQAPair.org_id == org_id
            )
        )

    async def vector_search(
        self,
        kb_id: UUID,
        query_embedding: List[float],
        top_k: int = 3,
        threshold: float = 0.85,
    ) -> List[Tuple[KnowledgeQAPair, float]]:
        """Semantic search against Q&A pairs — higher threshold for direct match."""
        if not VECTOR_AVAILABLE:
            return []

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        sql = text("""
            SELECT id, question, answer, tags, is_active, created_by, created_at, updated_at,
                   knowledge_base_id, org_id,
                   (1 - (embedding <=> CAST(:embedding AS vector))) AS score
            FROM knowledge_qa_pairs
            WHERE knowledge_base_id = :kb_id
              AND is_active = TRUE
              AND embedding IS NOT NULL
              AND (1 - (embedding <=> CAST(:embedding AS vector))) >= :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = await self.db.execute(sql, {
            "embedding": embedding_str,
            "kb_id": str(kb_id),
            "threshold": threshold,
            "top_k": top_k,
        })
        rows = result.mappings().all()

        pairs_with_scores = []
        for row in rows:
            qa = KnowledgeQAPair(
                id=row["id"],
                knowledge_base_id=row["knowledge_base_id"],
                org_id=row["org_id"],
                question=row["question"],
                answer=row["answer"],
                tags=row["tags"],
                is_active=row["is_active"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            pairs_with_scores.append((qa, float(row["score"])))

        return pairs_with_scores


class SyncLogRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, source_id: UUID, org_id: UUID) -> KnowledgeSyncLog:
        log = KnowledgeSyncLog(source_id=source_id, org_id=org_id)
        self.db.add(log)
        await self.db.flush()
        return log

    async def finish(self, log_id: UUID, status: str, **stats) -> None:
        stats["status"] = status
        stats["finished_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(KnowledgeSyncLog)
            .where(KnowledgeSyncLog.id == log_id)
            .values(**stats)
        )

    async def list_source(self, source_id: UUID, limit: int = 20) -> List[KnowledgeSyncLog]:
        result = await self.db.execute(
            select(KnowledgeSyncLog)
            .where(KnowledgeSyncLog.source_id == source_id)
            .order_by(KnowledgeSyncLog.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
