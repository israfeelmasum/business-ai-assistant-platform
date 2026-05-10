"""
Data Source model - Configuration for auto-pulling data from external APIs.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("client_id", "name", name="uq_data_source_client_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    api_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    auth_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    request_headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    pagination_type: Mapped[str] = mapped_column(String(20), default="none")
    pagination_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_path: Mapped[str] = mapped_column(String(255), default="")
    id_field: Mapped[str] = mapped_column(String(255), default="id")
    field_mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
