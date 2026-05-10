"""AI Knowledge model - Embeddings + summaries for semantic search."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base

class AIKnowledge(Base):
    __tablename__ = "ai_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_entities.id", ondelete="CASCADE"), nullable=False)
    entity_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entity_types.id", ondelete="CASCADE"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768))
    meta_data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict) # Fixed Attribute Name
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))