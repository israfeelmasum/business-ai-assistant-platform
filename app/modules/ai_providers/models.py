"""
AI Providers module — SQLAlchemy ORM models.
Tables: ai_providers, ai_provider_models, org_ai_providers
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    Numeric, Enum as SAEnum, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ProviderType(str, enum.Enum):
    openai      = "openai"
    anthropic   = "anthropic"
    google      = "google"
    ollama      = "ollama"
    groq        = "groq"
    mistral     = "mistral"
    custom      = "custom"


class ModelCapability(str, enum.Enum):
    chat        = "chat"
    embedding   = "embedding"
    vision      = "vision"
    tts         = "tts"
    stt         = "stt"
    translation = "translation"


class AiProvider(Base):
    """Platform-managed provider pool (Fellowly's own API keys)."""
    __tablename__ = "ai_providers"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(100), nullable=False)
    provider_type   = Column(SAEnum(ProviderType, name="provider_type"), nullable=False)
    base_url        = Column(Text)
    api_key_enc     = Column(Text)          # Encrypted; decrypted at runtime
    config          = Column(JSONB, default=dict)
    is_active       = Column(Boolean, nullable=False, default=True)
    is_default      = Column(Boolean, nullable=False, default=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    models = relationship("AiProviderModel", back_populates="provider",
                          cascade="all, delete-orphan")


class AiProviderModel(Base):
    """Individual model within a provider (e.g., gpt-4o, claude-3-5-sonnet)."""
    __tablename__ = "ai_provider_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_id", "capability",
                         name="uq_ai_provider_models"),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id         = Column(UUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id            = Column(String(100), nullable=False)
    display_name        = Column(String(150), nullable=False)
    capability          = Column(SAEnum(ModelCapability, name="model_capability"), nullable=False)
    context_window      = Column(Integer)
    max_tokens          = Column(Integer)
    cost_input_per_1m   = Column(Numeric(10, 6), default=0)
    cost_output_per_1m  = Column(Numeric(10, 6), default=0)
    is_active           = Column(Boolean, nullable=False, default=True)
    sort_order          = Column(Integer, nullable=False, default=0)

    # Relationships
    provider = relationship("AiProvider", back_populates="models")


class OrgAiProvider(Base):
    """BYOK — org brings their own API key for a specific provider."""
    __tablename__ = "org_ai_providers"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name            = Column(String(100), nullable=False)
    provider_type   = Column(SAEnum(ProviderType, name="provider_type", create_type=False), nullable=False)
    base_url        = Column(Text)
    api_key_enc     = Column(Text, nullable=False)  # Encrypted with platform secret
    config          = Column(JSONB, default=dict)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
