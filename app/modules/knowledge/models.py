"""
Knowledge Base module — SQLAlchemy ORM models.
Tables: knowledge_bases, knowledge_sources, knowledge_documents,
        knowledge_chunks, knowledge_qa_pairs, knowledge_sync_logs
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BigInteger,
    Enum as SAEnum, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    from sqlalchemy import Text as Vector  # fallback — vector queries won't work
    VECTOR_AVAILABLE = False


class SourceType(str, enum.Enum):
    file_upload     = "file_upload"
    url_crawl       = "url_crawl"
    api_sync        = "api_sync"
    manual_entry    = "manual_entry"
    database_sync   = "database_sync"
    sitemap         = "sitemap"


class DocumentStatus(str, enum.Enum):
    pending     = "pending"
    processing  = "processing"
    indexed     = "indexed"
    failed      = "failed"
    outdated    = "outdated"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    chatbot     = relationship("Chatbot", back_populates="knowledge_bases")
    sources     = relationship("KnowledgeSource", back_populates="knowledge_base", cascade="all, delete-orphan")
    documents   = relationship("KnowledgeDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks      = relationship("KnowledgeChunk", back_populates="knowledge_base", cascade="all, delete-orphan")
    qa_pairs    = relationship("KnowledgeQAPair", back_populates="knowledge_base", cascade="all, delete-orphan")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id       = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id                  = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type             = Column(SAEnum(SourceType, name="source_type"), nullable=False)
    name                    = Column(String(255), nullable=False)
    # API sync
    api_url                 = Column(Text)
    auth_type               = Column(String(30))
    auth_config             = Column(JSONB, default=dict)
    pagination_config       = Column(JSONB, default=dict)
    field_mapping           = Column(JSONB, default=dict)
    data_path               = Column(String(100))
    id_field                = Column(String(50), default="id")
    # URL crawl
    crawl_url               = Column(Text)
    crawl_depth             = Column(Integer, default=2)
    crawl_include_patterns  = Column(ARRAY(Text))
    crawl_exclude_patterns  = Column(ARRAY(Text))
    # Sync
    sync_interval_minutes   = Column(Integer, default=720)
    last_synced_at          = Column(DateTime(timezone=True))
    next_sync_at            = Column(DateTime(timezone=True))
    is_active               = Column(Boolean, nullable=False, default=True)
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    knowledge_base  = relationship("KnowledgeBase", back_populates="sources")
    documents       = relationship("KnowledgeDocument", back_populates="source")
    sync_logs       = relationship("KnowledgeSyncLog", back_populates="source", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id   = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id           = Column(UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="SET NULL"), nullable=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title               = Column(String(500))
    content_type        = Column(String(50))
    content_hash        = Column(String(64))
    raw_content         = Column(Text)
    file_url            = Column(Text)
    file_size_bytes     = Column(BigInteger)
    external_id         = Column(String(255))
    status              = Column(SAEnum(DocumentStatus, name="document_status"), nullable=False, default=DocumentStatus.pending)
    error_message       = Column(Text)
    extra_data            = Column("metadata", JSONB, default=dict)
    chunk_count         = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    knowledge_base  = relationship("KnowledgeBase", back_populates="documents")
    source          = relationship("KnowledgeSource", back_populates="documents")
    chunks          = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id         = Column(UUID(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_base_id   = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    content             = Column(Text, nullable=False)
    chunk_index         = Column(Integer, nullable=False)
    token_count         = Column(Integer)
    embedding           = Column(Vector(768) if VECTOR_AVAILABLE else Text)
    extra_data            = Column("metadata", JSONB, default=dict)
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    document        = relationship("KnowledgeDocument", back_populates="chunks")
    knowledge_base  = relationship("KnowledgeBase", back_populates="chunks")


class KnowledgeQAPair(Base):
    __tablename__ = "knowledge_qa_pairs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id   = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    question            = Column(Text, nullable=False)
    answer              = Column(Text, nullable=False)
    embedding           = Column(Vector(768) if VECTOR_AVAILABLE else Text)
    tags                = Column(ARRAY(Text))
    category            = Column(String(100))
    sort_order          = Column(Integer, nullable=False, default=0)
    is_active           = Column(Boolean, nullable=False, default=True)
    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="qa_pairs")


class KnowledgeSyncLog(Base):
    __tablename__ = "knowledge_sync_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id       = Column(UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    status          = Column(String(20), nullable=False, default="running")
    started_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at     = Column(DateTime(timezone=True))
    docs_created    = Column(Integer, default=0)
    docs_updated    = Column(Integer, default=0)
    docs_deleted    = Column(Integer, default=0)
    docs_skipped    = Column(Integer, default=0)
    docs_failed     = Column(Integer, default=0)
    chunks_created  = Column(Integer, default=0)
    errors          = Column(JSONB, default=list)

    # Relationships
    source = relationship("KnowledgeSource", back_populates="sync_logs")
