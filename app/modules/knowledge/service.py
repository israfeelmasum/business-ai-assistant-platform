"""
Knowledge Base module — business logic.
Handles KB CRUD, document upload/ingestion, Q&A management, RAG search.
"""

import hashlib
import io
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeBase, KnowledgeDocument, KnowledgeQAPair,
    DocumentStatus, SourceType
)
from app.modules.knowledge.pipeline import RAGPipeline, content_hash
from app.modules.knowledge.repository import (
    KBRepository, SourceRepository, DocumentRepository,
    ChunkRepository, QAPairRepository, SyncLogRepository
)
from app.modules.knowledge.schemas import (
    KBCreateRequest, KBUpdateRequest, KBResponse,
    SourceCreateRequest, SourceUpdateRequest, SourceResponse,
    DocumentResponse, QAPairCreateRequest, QAPairUpdateRequest, QAPairResponse,
    QAPairReorderRequest,
    SyncLogResponse, RAGSearchRequest, RAGSearchResult,
)
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)

# Max file size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024


class KnowledgeService:

    def __init__(self, db: AsyncSession, embedding_config: Optional[dict] = None):
        self.db         = db
        self.kbs        = KBRepository(db)
        self.sources    = SourceRepository(db)
        self.docs       = DocumentRepository(db)
        self.chunks     = ChunkRepository(db)
        self.qa_pairs   = QAPairRepository(db)
        self.sync_logs  = SyncLogRepository(db)
        self.members    = MemberRepository(db)
        self.pipeline   = RAGPipeline(db, embedding_config)

    # ── Knowledge Base CRUD ────────────────────────────────────────────────────

    async def create_kb(
        self, org_id: UUID, chatbot_id: UUID, req: KBCreateRequest, requester_id: UUID
    ) -> KBResponse:
        await self._require_admin(org_id, requester_id)
        kb = await self.kbs.create(chatbot_id, org_id, req.name, req.description)
        await self.db.commit()
        await self.db.refresh(kb)
        return KBResponse.model_validate(kb)

    async def list_kbs(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> List[KBResponse]:
        await self._require_member(org_id, requester_id)
        kbs = await self.kbs.list_chatbot(chatbot_id)
        return [KBResponse.model_validate(kb) for kb in kbs]

    async def get_kb(self, org_id: UUID, kb_id: UUID, requester_id: UUID) -> KBResponse:
        await self._require_member(org_id, requester_id)
        kb = await self._get_kb_or_404(kb_id, org_id)
        return KBResponse.model_validate(kb)

    async def update_kb(
        self, org_id: UUID, kb_id: UUID, req: KBUpdateRequest, requester_id: UUID
    ) -> KBResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        kb = await self.kbs.update(kb_id, org_id, **updates)
        await self.db.commit()
        return KBResponse.model_validate(kb)

    async def delete_kb(self, org_id: UUID, kb_id: UUID, requester_id: UUID) -> None:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        await self.kbs.delete(kb_id, org_id)
        await self.db.commit()

    # ── Sources ────────────────────────────────────────────────────────────────

    async def create_source(
        self, org_id: UUID, kb_id: UUID, req: SourceCreateRequest, requester_id: UUID
    ) -> SourceResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        src = await self.sources.create(kb_id, org_id, **req.model_dump())
        await self.db.commit()
        await self.db.refresh(src)
        return SourceResponse.model_validate(src)

    async def list_sources(
        self, org_id: UUID, kb_id: UUID, requester_id: UUID
    ) -> List[SourceResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        srcs = await self.sources.list_kb(kb_id)
        return [SourceResponse.model_validate(s) for s in srcs]

    async def update_source(
        self, org_id: UUID, kb_id: UUID, source_id: UUID,
        req: SourceUpdateRequest, requester_id: UUID
    ) -> SourceResponse:
        await self._require_admin(org_id, requester_id)
        updates = req.model_dump(exclude_unset=True)
        src = await self.sources.update(source_id, **updates)
        if not src or src.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Source not found")
        await self.db.commit()
        return SourceResponse.model_validate(src)

    async def delete_source(
        self, org_id: UUID, kb_id: UUID, source_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self.sources.delete(source_id, org_id)
        await self.db.commit()

    # ── Document Upload ────────────────────────────────────────────────────────

    async def upload_document(
        self, org_id: UUID, kb_id: UUID, file: UploadFile,
        requester_id: UUID, source_id: Optional[UUID] = None
    ) -> DocumentResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB."
            )

        # Detect content type from filename
        filename = file.filename or "unknown"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        supported = {"pdf", "docx", "doc", "txt", "csv", "json", "html", "htm", "md", "xlsx"}
        if ext not in supported:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: .{ext}"
            )

        raw_text = await self._extract_text(content, ext)
        c_hash = content_hash(raw_text)

        # Skip if identical document already indexed
        existing = await self.docs.get_by_hash(kb_id, c_hash)
        if existing and existing.status == DocumentStatus.indexed:
            return DocumentResponse.model_validate(existing)

        doc = await self.docs.create(
            kb_id=kb_id,
            org_id=org_id,
            title=filename,
            content_type=ext,
            content_hash=c_hash,
            raw_content=raw_text,
            file_size_bytes=len(content),
            source_id=source_id,
            status=DocumentStatus.pending,
        )
        await self.db.commit()

        # Ingest in the same request (async — acceptable for small files)
        chunk_count = await self.pipeline.ingest_document(doc.id, org_id)
        await self.db.commit()

        doc = await self.docs.get_by_id(doc.id)
        return DocumentResponse.model_validate(doc)

    async def add_manual_document(
        self, org_id: UUID, kb_id: UUID,
        title: str, content: str, requester_id: UUID
    ) -> DocumentResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)

        c_hash = content_hash(content)
        doc = await self.docs.create(
            kb_id=kb_id, org_id=org_id,
            title=title, content_type="manual",
            content_hash=c_hash, raw_content=content,
            status=DocumentStatus.pending,
        )
        await self.db.commit()

        await self.pipeline.ingest_document(doc.id, org_id)
        await self.db.commit()

        doc = await self.docs.get_by_id(doc.id)
        return DocumentResponse.model_validate(doc)

    async def list_documents(
        self, org_id: UUID, kb_id: UUID, requester_id: UUID,
        status_filter: Optional[DocumentStatus] = None,
        limit: int = 50, offset: int = 0
    ) -> List[DocumentResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        docs = await self.docs.list_kb(kb_id, status_filter, limit, offset)
        return [DocumentResponse.model_validate(d) for d in docs]

    async def delete_document(
        self, org_id: UUID, kb_id: UUID, doc_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self.docs.delete(doc_id, org_id)
        await self.db.commit()

    async def reindex_document(
        self, org_id: UUID, kb_id: UUID, doc_id: UUID, requester_id: UUID
    ) -> DocumentResponse:
        await self._require_admin(org_id, requester_id)
        doc = await self.docs.get_by_id(doc_id)
        if not doc or doc.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Document not found")
        await self.pipeline.ingest_document(doc_id, org_id)
        await self.db.commit()
        doc = await self.docs.get_by_id(doc_id)
        return DocumentResponse.model_validate(doc)

    # ── Q&A Pairs ──────────────────────────────────────────────────────────────

    async def create_qa_pair(
        self, org_id: UUID, kb_id: UUID, req: QAPairCreateRequest, requester_id: UUID
    ) -> QAPairResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)

        qa = await self.qa_pairs.create(
            kb_id=kb_id, org_id=org_id,
            question=req.question, answer=req.answer,
            created_by=requester_id, tags=req.tags,
            category=req.category, sort_order=req.sort_order,
        )
        await self.db.commit()

        # Embed asynchronously (same request for now)
        await self.pipeline.embed_qa_pair(qa.id, org_id)
        await self.db.commit()

        qa = await self.qa_pairs.get_by_id(qa.id, org_id)
        return QAPairResponse.model_validate(qa)

    async def list_qa_pairs(
        self, org_id: UUID, kb_id: UUID, requester_id: UUID,
        category: Optional[str] = None,
        limit: int = 200, offset: int = 0
    ) -> List[QAPairResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        pairs = await self.qa_pairs.list_kb(kb_id, active_only=False, category=category, limit=limit, offset=offset)
        return [QAPairResponse.model_validate(p) for p in pairs]

    async def reorder_qa_pairs(
        self, org_id: UUID, kb_id: UUID, req: "QAPairReorderRequest", requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        items = [{"id": item.id, "sort_order": item.sort_order} for item in req.items]
        await self.qa_pairs.bulk_reorder(items, org_id)
        await self.db.commit()

    async def update_qa_pair(
        self, org_id: UUID, kb_id: UUID, qa_id: UUID,
        req: QAPairUpdateRequest, requester_id: UUID
    ) -> QAPairResponse:
        await self._require_admin(org_id, requester_id)
        updates = req.model_dump(exclude_unset=True)
        qa = await self.qa_pairs.update(qa_id, org_id, **updates)
        if not qa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Q&A pair not found")
        # Re-embed if question changed
        if "question" in updates:
            await self.pipeline.embed_qa_pair(qa_id, org_id)
        await self.db.commit()
        qa = await self.qa_pairs.get_by_id(qa_id, org_id)
        return QAPairResponse.model_validate(qa)

    async def delete_qa_pair(
        self, org_id: UUID, kb_id: UUID, qa_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self.qa_pairs.delete(qa_id, org_id)
        await self.db.commit()

    # ── Bulk Training Data Upload ───────────────────────────────────────────────

    async def upload_training_data(
        self,
        org_id: UUID,
        kb_id: UUID,
        file: UploadFile,
        requester_id: UUID,
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Parse an Excel or CSV training data file and bulk-insert Q&A pairs
        into the specified knowledge base with embeddings.

        Supported column names (case-insensitive):
          question   : question / primary question / q / title
          answer     : answer / long answer / a / response / description
          category   : category / type / topic
          sub_cat    : sub-category / sub category / subcategory / tags
          suggestion : linkable suggestion / suggestion / link suggestion
          relevant_q : relevant questions / related questions
        """
        await self._require_admin(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)

        # ── Read file ──────────────────────────────────────────────────────────
        content = await file.read()
        filename = (file.filename or "").lower()

        try:
            import pandas as pd
            if filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content))
            elif filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Unsupported file type. Use .xlsx, .xls, or .csv",
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse file: {e}",
            )

        # ── Map columns ────────────────────────────────────────────────────────
        COL_ALIASES: Dict[str, str] = {
            "question": "question", "primary question": "question",
            "q": "question", "title": "question",
            "answer": "answer", "long answer": "answer",
            "a": "answer", "response": "answer", "description": "answer",
            "short answer": "short_answer",
            "category": "category", "type": "category", "topic": "category",
            "sub-category": "sub_category", "sub category": "sub_category",
            "subcategory": "sub_category", "tags": "sub_category",
            "relevant questions": "relevant_questions",
            "related questions": "relevant_questions",
            "linkable suggestion": "suggestion",
            "suggestion": "suggestion", "link suggestion": "suggestion",
        }
        mapping: Dict[str, str] = {}
        for col in df.columns:
            canonical = COL_ALIASES.get(col.strip().lower())
            if canonical:
                mapping[canonical] = col

        if "question" not in mapping:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No question column found. Expected one of: question, 'primary question', q, title. Got: {list(df.columns)}",
            )
        if "answer" not in mapping and "short_answer" not in mapping:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No answer column found. Expected one of: answer, 'long answer', a, response, description. Got: {list(df.columns)}",
            )

        import pandas as _pd

        def get_cell(row: Any, field: str, default: str = "") -> str:
            col = mapping.get(field)
            if col and col in row.index:
                val = row[col]
                if _pd.notna(val):
                    return str(val).strip()
            return default

        # ── Build normalized rows ──────────────────────────────────────────────
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            question = get_cell(row, "question")
            if not question:
                continue
            answer = get_cell(row, "answer") or get_cell(row, "short_answer")
            if not answer:
                continue

            suggestion = get_cell(row, "suggestion")
            if suggestion:
                answer = f"{answer}\n\n{suggestion}"

            cat_parts = [p for p in [get_cell(row, "category"), get_cell(row, "sub_category")] if p]
            category = " / ".join(cat_parts) if cat_parts else None

            tag_list: List[str] = []
            sub_cat = get_cell(row, "sub_category")
            cat_val = get_cell(row, "category")
            if sub_cat:
                tag_list.append(sub_cat)
            if cat_val and cat_val not in tag_list:
                tag_list.append(cat_val)
            rel_qs = get_cell(row, "relevant_questions")
            if rel_qs:
                for q in rel_qs.replace(" / ", "/").split("/"):
                    q = q.strip()
                    if q and len(q) < 120:
                        tag_list.append(q)

            rows.append({"question": question, "answer": answer,
                         "category": category, "tags": tag_list})

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No valid Q&A rows found in file.",
            )

        # ── Clear existing if requested ────────────────────────────────────────
        if clear_existing:
            from sqlalchemy import delete
            from app.modules.knowledge.models import KnowledgeQAPair
            await self.db.execute(
                delete(KnowledgeQAPair).where(
                    KnowledgeQAPair.knowledge_base_id == kb_id,
                    KnowledgeQAPair.org_id == org_id,
                )
            )
            await self.db.flush()

        # ── Get max sort_order ─────────────────────────────────────────────────
        from sqlalchemy import select, func
        from app.modules.knowledge.models import KnowledgeQAPair
        max_order_result = await self.db.execute(
            select(func.coalesce(func.max(KnowledgeQAPair.sort_order), -1))
            .where(KnowledgeQAPair.knowledge_base_id == kb_id)
        )
        max_order = max_order_result.scalar() or -1

        # ── Insert rows ────────────────────────────────────────────────────────
        inserted = 0
        for idx, row in enumerate(rows):
            qa = await self.qa_pairs.create(
                kb_id=kb_id, org_id=org_id,
                question=row["question"], answer=row["answer"],
                created_by=requester_id,
                tags=row["tags"],
                category=row["category"],
                sort_order=max_order + 1 + idx,
            )
            inserted += 1

        await self.db.commit()

        # ── Batch-embed newly inserted rows ────────────────────────────────────
        logger.info(f"Batch-embedding {inserted} Q&A pairs for KB {kb_id}...")
        from sqlalchemy import select as _select
        from app.modules.knowledge.models import KnowledgeQAPair as _QA
        _result = await self.db.execute(
            _select(_QA).where(
                _QA.knowledge_base_id == kb_id,
                _QA.org_id == org_id,
                _QA.embedding == None,  # noqa: E711
            ).limit(inserted + 10)
        )
        new_pairs = list(_result.scalars().all())
        embedded = await self.pipeline.embed_qa_pairs_batch(new_pairs, org_id)

        await self.db.commit()
        logger.info(f"Training data upload complete: {inserted} rows, {embedded} embedded.")

        return {
            "inserted": inserted,
            "embedded": embedded,
            "skipped": len(df) - inserted,
            "total_in_file": len(df),
            "clear_existing": clear_existing,
            "kb_id": str(kb_id),
        }

    # ── RAG Search ─────────────────────────────────────────────────────────────

    async def search(
        self, org_id: UUID, kb_id: UUID,
        req: RAGSearchRequest, requester_id: UUID
    ) -> List[RAGSearchResult]:
        await self._require_member(org_id, requester_id)
        await self._get_kb_or_404(kb_id, org_id)
        return await self.pipeline.search(
            kb_id=kb_id,
            query=req.query,
            top_k=req.top_k,
            threshold=req.threshold,
        )

    # ── Sync Logs ──────────────────────────────────────────────────────────────

    async def list_sync_logs(
        self, org_id: UUID, kb_id: UUID, source_id: UUID, requester_id: UUID
    ) -> List[SyncLogResponse]:
        await self._require_member(org_id, requester_id)
        logs = await self.sync_logs.list_source(source_id)
        return [SyncLogResponse.model_validate(log) for log in logs]

    # ── Text Extraction ────────────────────────────────────────────────────────

    async def _extract_text(self, content: bytes, ext: str) -> str:
        """Extract raw text from various file formats."""
        try:
            if ext == "pdf":
                return self._extract_pdf(content)
            elif ext in ("docx", "doc"):
                return self._extract_docx(content)
            elif ext == "csv":
                return content.decode("utf-8", errors="replace")
            elif ext in ("html", "htm"):
                return self._extract_html(content)
            elif ext == "json":
                import json
                data = json.loads(content.decode("utf-8", errors="replace"))
                return json.dumps(data, ensure_ascii=False, indent=2)
            else:
                return content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Text extraction fallback for .{ext}: {e}")
            return content.decode("utf-8", errors="replace")

    def _extract_pdf(self, content: bytes) -> str:
        try:
            import pypdf
            import io
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            try:
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    return "\n".join(page.extract_text() or "" for page in pdf.pages)
            except ImportError:
                return content.decode("utf-8", errors="replace")

    def _extract_docx(self, content: bytes) -> str:
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            return content.decode("utf-8", errors="replace")

    def _extract_html(self, content: bytes) -> str:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            import re
            text = content.decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", text)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_kb_or_404(self, kb_id: UUID, org_id: UUID) -> KnowledgeBase:
        kb = await self.kbs.get_by_id(kb_id, org_id)
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Knowledge base not found")
        return kb

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")

    async def _require_admin(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
        if member.role not in ("admin",):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admin role required")
