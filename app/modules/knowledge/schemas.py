"""
Knowledge Base module — Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.knowledge.models import SourceType, DocumentStatus


# ── Knowledge Base ─────────────────────────────────────────────────────────────

class KBCreateRequest(BaseModel):
    name:           str
    description:    Optional[str] = None


class KBUpdateRequest(BaseModel):
    name:           Optional[str] = None
    description:    Optional[str] = None
    is_active:      Optional[bool] = None


class KBResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    chatbot_id:     UUID
    org_id:         UUID
    name:           str
    description:    Optional[str]
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime


# ── Knowledge Sources ──────────────────────────────────────────────────────────

class SourceCreateRequest(BaseModel):
    source_type:            SourceType
    name:                   str
    # API sync fields
    api_url:                Optional[str] = None
    auth_type:              Optional[str] = None
    auth_config:            Optional[Dict[str, Any]] = None
    pagination_config:      Optional[Dict[str, Any]] = None
    field_mapping:          Optional[Dict[str, Any]] = None
    data_path:              Optional[str] = None
    id_field:               Optional[str] = "id"
    # URL crawl fields
    crawl_url:              Optional[str] = None
    crawl_depth:            Optional[int] = 2
    crawl_include_patterns: Optional[List[str]] = None
    crawl_exclude_patterns: Optional[List[str]] = None
    # Sync schedule
    sync_interval_minutes:  int = 720


class SourceUpdateRequest(BaseModel):
    name:                   Optional[str] = None
    api_url:                Optional[str] = None
    auth_config:            Optional[Dict[str, Any]] = None
    crawl_url:              Optional[str] = None
    crawl_depth:            Optional[int] = None
    sync_interval_minutes:  Optional[int] = None
    is_active:              Optional[bool] = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     UUID
    knowledge_base_id:      UUID
    org_id:                 UUID
    source_type:            SourceType
    name:                   str
    api_url:                Optional[str]
    crawl_url:              Optional[str]
    crawl_depth:            Optional[int]
    sync_interval_minutes:  int
    last_synced_at:         Optional[datetime]
    next_sync_at:           Optional[datetime]
    is_active:              bool
    created_at:             datetime
    updated_at:             datetime


# ── Documents ──────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    knowledge_base_id:  UUID
    org_id:             UUID
    title:              Optional[str]
    content_type:       Optional[str]
    file_url:           Optional[str]
    file_size_bytes:    Optional[int]
    status:             DocumentStatus
    error_message:      Optional[str]
    chunk_count:        int
    extra_data:         Dict[str, Any] = Field(default_factory=dict)
    created_at:         datetime
    updated_at:         datetime


# ── Chunks ─────────────────────────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    document_id:        UUID
    knowledge_base_id:  UUID
    content:            str
    chunk_index:        int
    token_count:        Optional[int]
    extra_data:         Dict[str, Any] = Field(default_factory=dict)
    created_at:         datetime


# ── Q&A Pairs ──────────────────────────────────────────────────────────────────

class QAPairCreateRequest(BaseModel):
    question:   str
    answer:     str
    tags:       Optional[List[str]] = None
    category:   Optional[str] = None
    sort_order: int = 0

    @field_validator("question", "answer")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Cannot be empty")
        return v.strip()


class QAPairUpdateRequest(BaseModel):
    question:   Optional[str] = None
    answer:     Optional[str] = None
    tags:       Optional[List[str]] = None
    category:   Optional[str] = None
    sort_order: Optional[int] = None
    is_active:  Optional[bool] = None


class QAPairReorderItem(BaseModel):
    id:         UUID
    sort_order: int


class QAPairReorderRequest(BaseModel):
    items: List[QAPairReorderItem]


class QAPairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    knowledge_base_id:  UUID
    org_id:             UUID
    question:           str
    answer:             str
    tags:               Optional[List[str]]
    category:           Optional[str] = None
    sort_order:         int = 0
    is_active:          bool
    created_by:         Optional[UUID]
    created_at:         datetime
    updated_at:         datetime


# ── Sync Logs ──────────────────────────────────────────────────────────────────

class SyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    source_id:      UUID
    status:         str
    started_at:     datetime
    finished_at:    Optional[datetime]
    docs_created:   int
    docs_updated:   int
    docs_deleted:   int
    docs_skipped:   int
    docs_failed:    int
    chunks_created: int
    errors:         List[Any]


# ── RAG Search ─────────────────────────────────────────────────────────────────

class RAGSearchResult(BaseModel):
    chunk_id:       UUID
    document_id:    UUID
    content:        str
    score:          float
    metadata:       Dict[str, Any]
    source_type:    str = "chunk"  # chunk | qa_pair


class RAGSearchRequest(BaseModel):
    query:      str
    top_k:      int = 5
    threshold:  float = 0.7
