"""
Knowledge Base router — KB management, sources, documents, Q&A, RAG search.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.knowledge.models import DocumentStatus
from app.modules.knowledge.schemas import (
    KBCreateRequest, KBUpdateRequest, KBResponse,
    SourceCreateRequest, SourceUpdateRequest, SourceResponse,
    DocumentResponse,
    QAPairCreateRequest, QAPairUpdateRequest, QAPairResponse,
    QAPairReorderRequest,
    SyncLogResponse, RAGSearchRequest, RAGSearchResult,
)
from app.modules.knowledge.service import KnowledgeService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Knowledge Base"])


# ── Knowledge Bases ────────────────────────────────────────────────────────────

@router.post("/organizations/{org_id}/chatbots/{chatbot_id}/knowledge-bases",
             response_model=KBResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    org_id: UUID, chatbot_id: UUID,
    req: KBCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a knowledge base for a chatbot. Admin only."""
    svc = KnowledgeService(db)
    return await svc.create_kb(org_id, chatbot_id, req, requester_id=current_user.id)


@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/knowledge-bases",
            response_model=List[KBResponse])
async def list_knowledge_bases(
    org_id: UUID, chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.list_kbs(org_id, chatbot_id, requester_id=current_user.id)


@router.get("/organizations/{org_id}/knowledge-bases/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(
    org_id: UUID, kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.get_kb(org_id, kb_id, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/knowledge-bases/{kb_id}", response_model=KBResponse)
async def update_knowledge_base(
    org_id: UUID, kb_id: UUID,
    req: KBUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.update_kb(org_id, kb_id, req, requester_id=current_user.id)


@router.delete("/organizations/{org_id}/knowledge-bases/{kb_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    org_id: UUID, kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    await svc.delete_kb(org_id, kb_id, requester_id=current_user.id)


# ── Sources ────────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/knowledge-bases/{kb_id}/sources",
            response_model=List[SourceResponse])
async def list_sources(
    org_id: UUID, kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.list_sources(org_id, kb_id, requester_id=current_user.id)


@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/sources",
             response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    org_id: UUID, kb_id: UUID,
    req: SourceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a knowledge source (API sync, URL crawl, etc.). Admin only."""
    svc = KnowledgeService(db)
    return await svc.create_source(org_id, kb_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/knowledge-bases/{kb_id}/sources/{source_id}",
              response_model=SourceResponse)
async def update_source(
    org_id: UUID, kb_id: UUID, source_id: UUID,
    req: SourceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.update_source(org_id, kb_id, source_id, req,
                                   requester_id=current_user.id)


@router.delete("/organizations/{org_id}/knowledge-bases/{kb_id}/sources/{source_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    org_id: UUID, kb_id: UUID, source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    await svc.delete_source(org_id, kb_id, source_id, requester_id=current_user.id)


# ── Documents ──────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/knowledge-bases/{kb_id}/documents",
            response_model=List[DocumentResponse])
async def list_documents(
    org_id: UUID, kb_id: UUID,
    status_filter: Optional[DocumentStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.list_documents(org_id, kb_id, requester_id=current_user.id,
                                    status_filter=status_filter, limit=limit, offset=offset)


@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/documents/upload",
             response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    org_id: UUID, kb_id: UUID,
    file: UploadFile = File(...),
    source_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file (PDF, DOCX, TXT, CSV, etc.) and auto-ingest. Admin only."""
    svc = KnowledgeService(db)
    return await svc.upload_document(org_id, kb_id, file,
                                     requester_id=current_user.id, source_id=source_id)


@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/documents/manual",
             response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_manual_document(
    org_id: UUID, kb_id: UUID,
    title: str = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a manual text document and ingest it. Admin only."""
    svc = KnowledgeService(db)
    return await svc.add_manual_document(org_id, kb_id, title, content,
                                         requester_id=current_user.id)


@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/documents/{doc_id}/reindex",
             response_model=DocumentResponse)
async def reindex_document(
    org_id: UUID, kb_id: UUID, doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Force re-chunk and re-embed a document. Admin only."""
    svc = KnowledgeService(db)
    return await svc.reindex_document(org_id, kb_id, doc_id, requester_id=current_user.id)


@router.delete("/organizations/{org_id}/knowledge-bases/{kb_id}/documents/{doc_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    org_id: UUID, kb_id: UUID, doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    await svc.delete_document(org_id, kb_id, doc_id, requester_id=current_user.id)


# ── Training Data Upload ────────────────────────────────────────────────────────

@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/training-data/upload",
             status_code=status.HTTP_200_OK)
async def upload_training_data(
    org_id: UUID,
    kb_id: UUID,
    file: UploadFile = File(..., description="Excel (.xlsx/.xls) or CSV file with Q&A training data"),
    clear_existing: bool = Form(False, description="Delete all existing Q&A pairs before inserting"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk upload training data for a knowledge base.

    Accepts Excel or CSV files with columns:
    - **question** (required): primary question / q / title
    - **answer** (required): answer / long answer / response / description
    - **category** (optional): category / type / topic
    - **sub-category** (optional): sub-category / subcategory / tags
    - **relevant questions** (optional): slash-separated alternate questions
    - **linkable suggestion** (optional): HTML suggestion appended to answer

    Each row is inserted as a Q&A pair with a vector embedding for RAG search.
    Admin access required.
    """
    svc = KnowledgeService(db)
    return await svc.upload_training_data(
        org_id=org_id, kb_id=kb_id, file=file,
        requester_id=current_user.id, clear_existing=clear_existing,
    )


# ── Q&A Pairs ──────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/knowledge-bases/{kb_id}/qa-pairs",
            response_model=List[QAPairResponse])
async def list_qa_pairs(
    org_id: UUID, kb_id: UUID,
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.list_qa_pairs(org_id, kb_id, requester_id=current_user.id,
                                   category=category, limit=limit, offset=offset)


@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/qa-pairs",
             response_model=QAPairResponse, status_code=status.HTTP_201_CREATED)
async def create_qa_pair(
    org_id: UUID, kb_id: UUID,
    req: QAPairCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a Q&A pair for direct training. Admin only."""
    svc = KnowledgeService(db)
    return await svc.create_qa_pair(org_id, kb_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/knowledge-bases/{kb_id}/qa-pairs/reorder",
              status_code=status.HTTP_204_NO_CONTENT)
async def reorder_qa_pairs(
    org_id: UUID, kb_id: UUID,
    req: QAPairReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk update sort_order for Q&A pairs (drag-and-drop reorder)."""
    svc = KnowledgeService(db)
    await svc.reorder_qa_pairs(org_id, kb_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/knowledge-bases/{kb_id}/qa-pairs/{qa_id}",
              response_model=QAPairResponse)
async def update_qa_pair(
    org_id: UUID, kb_id: UUID, qa_id: UUID,
    req: QAPairUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.update_qa_pair(org_id, kb_id, qa_id, req,
                                    requester_id=current_user.id)


@router.delete("/organizations/{org_id}/knowledge-bases/{kb_id}/qa-pairs/{qa_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_qa_pair(
    org_id: UUID, kb_id: UUID, qa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    await svc.delete_qa_pair(org_id, kb_id, qa_id, requester_id=current_user.id)


# ── RAG Search ─────────────────────────────────────────────────────────────────

@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/search",
             response_model=List[RAGSearchResult])
async def rag_search(
    org_id: UUID, kb_id: UUID,
    req: RAGSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic similarity search against the knowledge base. For testing/debugging."""
    svc = KnowledgeService(db)
    return await svc.search(org_id, kb_id, req, requester_id=current_user.id)


# ── Sync Embeddings (re-embed any Q&A pairs with missing embeddings) ──────────

@router.post("/organizations/{org_id}/knowledge-bases/{kb_id}/sync-embeddings",
             status_code=200)
async def sync_embeddings(
    org_id: UUID, kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-embed any Q&A pairs in this KB that have no embedding yet.
    Call this after adding new Q&A pairs via the admin UI to ensure
    they are immediately searchable.
    """
    from sqlalchemy import select as _select
    from app.modules.knowledge.models import KnowledgeQAPair as _QA
    from app.modules.knowledge.pipeline import RAGPipeline
    from app.modules.ai_providers.service import AiProviderService
    from app.modules.ai_providers.models import ModelCapability

    svc = KnowledgeService(db)
    await svc._require_admin(org_id, current_user.id)

    # Resolve embedding provider for this org
    ai_svc = AiProviderService(db)
    embedding_config = await ai_svc.resolve_provider_key(
        org_id=org_id, capability=ModelCapability.embedding
    )
    pipeline = RAGPipeline(db, embedding_config)

    # Find unembedded Q&A pairs in this KB
    result = await db.execute(
        _select(_QA).where(
            _QA.knowledge_base_id == kb_id,
            _QA.org_id == org_id,
            _QA.embedding == None,  # noqa: E711
        ).limit(500)
    )
    unembedded = list(result.scalars().all())
    embedded_count = 0
    if unembedded:
        embedded_count = await pipeline.embed_qa_pairs_batch(unembedded, org_id)
        await db.commit()

    return {"synced": embedded_count, "total_unembedded": len(unembedded)}


# ── Sync Logs ──────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/knowledge-bases/{kb_id}/sources/{source_id}/sync-logs",
            response_model=List[SyncLogResponse])
async def list_sync_logs(
    org_id: UUID, kb_id: UUID, source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = KnowledgeService(db)
    return await svc.list_sync_logs(org_id, kb_id, source_id, requester_id=current_user.id)
