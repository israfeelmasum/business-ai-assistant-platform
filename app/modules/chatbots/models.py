"""
Chatbots module — SQLAlchemy ORM models.
Tables: chatbots, chatbot_model_config, chatbot_personas, chatbot_prompts,
        chatbot_guardrails, chatbot_deployments, chatbot_themes, chatbot_prechat_forms
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    Numeric, Enum as SAEnum, ForeignKey, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PersonalityType(str, enum.Enum):
    professional    = "professional"
    friendly        = "friendly"
    formal          = "formal"
    playful         = "playful"
    empathetic      = "empathetic"


class DomainType(str, enum.Enum):
    general         = "general"
    medical         = "medical"
    legal           = "legal"
    tech            = "tech"
    retail          = "retail"
    education       = "education"
    finance         = "finance"
    real_estate     = "real_estate"
    hospitality     = "hospitality"


class FallbackBehavior(str, enum.Enum):
    escalate    = "escalate"
    clarify     = "clarify"
    suggest     = "suggest"
    apologize   = "apologize"


class PromptLayer(str, enum.Enum):
    foundation  = "foundation"
    tenant      = "tenant"
    contextual  = "contextual"
    guardrail   = "guardrail"


class DeploymentChannel(str, enum.Enum):
    web_widget      = "web_widget"
    mobile_sdk      = "mobile_sdk"
    whatsapp        = "whatsapp"
    telegram        = "telegram"
    slack           = "slack"
    rest_api        = "rest_api"
    facebook        = "facebook"


class ProviderSource(str, enum.Enum):
    platform    = "platform"
    org_custom  = "org_custom"


class Chatbot(Base):
    __tablename__ = "chatbots"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_chatbot_org_slug"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name            = Column(String(255), nullable=False)
    slug            = Column(String(100), nullable=False)
    description     = Column(Text)
    avatar_url      = Column(Text)
    is_active       = Column(Boolean, nullable=False, default=True)
    is_published    = Column(Boolean, nullable=False, default=False)
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    model_configs   = relationship("ChatbotModelConfig", back_populates="chatbot", cascade="all, delete-orphan")
    personas        = relationship("ChatbotPersona", back_populates="chatbot", cascade="all, delete-orphan")
    prompts         = relationship("ChatbotPrompt", back_populates="chatbot", cascade="all, delete-orphan")
    guardrails      = relationship("ChatbotGuardrail", back_populates="chatbot", cascade="all, delete-orphan")
    deployments     = relationship("ChatbotDeployment", back_populates="chatbot", cascade="all, delete-orphan")
    theme           = relationship("ChatbotTheme", back_populates="chatbot", uselist=False, cascade="all, delete-orphan")
    prechat_form    = relationship("ChatbotPrechatForm", back_populates="chatbot", uselist=False, cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="chatbot", cascade="all, delete-orphan")


class ChatbotModelConfig(Base):
    """Which AI model to use for each capability task."""
    __tablename__ = "chatbot_model_config"
    __table_args__ = (UniqueConstraint("chatbot_id", "task", name="uq_chatbot_model_task"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id          = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    task                = Column(SAEnum("chat", "embedding", "vision", "tts", "stt", "translation",
                                       name="model_capability", create_type=False), nullable=False)
    provider_source     = Column(SAEnum(ProviderSource, name="provider_source"), nullable=False, default=ProviderSource.platform)
    provider_id         = Column(UUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True)
    org_provider_id     = Column(UUID(as_uuid=True), ForeignKey("org_ai_providers.id", ondelete="SET NULL"), nullable=True)
    model_id            = Column(String(100), nullable=False)
    parameters          = Column(JSONB, default=lambda: {"temperature": 0.7, "max_tokens": 1024})
    is_active           = Column(Boolean, nullable=False, default=True)

    chatbot = relationship("Chatbot", back_populates="model_configs")


class ChatbotPersona(Base):
    __tablename__ = "chatbot_personas"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id              = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_name            = Column(String(100), nullable=False, default="Assistant")
    personality             = Column(SAEnum(PersonalityType, name="personality_type"), nullable=False, default=PersonalityType.professional)
    domain                  = Column(SAEnum(DomainType, name="domain_type"), nullable=False, default=DomainType.general)
    default_language        = Column(String(10), nullable=False, default="en")
    supported_languages     = Column(ARRAY(String(10)), nullable=False, default=lambda: ["en"])
    greeting_message        = Column(Text)
    farewell_message        = Column(Text)
    offline_message         = Column(Text)
    fallback_behavior       = Column(SAEnum(FallbackBehavior, name="fallback_behavior"), nullable=False, default=FallbackBehavior.escalate)
    voice_id                = Column(String(100))
    voice_speed             = Column(Numeric(3, 1), default=1.0)
    is_active               = Column(Boolean, nullable=False, default=True)
    version                 = Column(Integer, nullable=False, default=1)
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="personas")


class ChatbotPrompt(Base):
    """4-layer system prompt architecture: foundation > tenant > contextual > guardrail."""
    __tablename__ = "chatbot_prompts"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    layer       = Column(SAEnum(PromptLayer, name="prompt_layer"), nullable=False)
    name        = Column(String(150), nullable=False)
    content     = Column(Text, nullable=False)
    is_active   = Column(Boolean, nullable=False, default=True)
    version     = Column(Integer, nullable=False, default=1)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="prompts")


class ChatbotGuardrail(Base):
    __tablename__ = "chatbot_guardrails"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    name        = Column(String(150), nullable=False)
    rule_type   = Column(String(50), nullable=False)
    rule_config = Column(JSONB, nullable=False, default=dict)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="guardrails")


class ChatbotDeployment(Base):
    __tablename__ = "chatbot_deployments"
    __table_args__ = (UniqueConstraint("chatbot_id", "channel", name="uq_chatbot_deployment_channel"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel     = Column(SAEnum(DeploymentChannel, name="deployment_channel"), nullable=False)
    name        = Column(String(100))
    config      = Column(JSONB, default=dict)
    api_key_id  = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="deployments")


class ChatbotTheme(Base):
    __tablename__ = "chatbot_themes"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id              = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    color_primary           = Column(String(7), default="#2563EB")
    color_secondary         = Column(String(7), default="#7C3AED")
    color_accent            = Column(String(7), default="#06B6D4")
    color_background        = Column(String(7), default="#FFFFFF")
    color_text              = Column(String(7), default="#111827")
    color_user_bubble       = Column(String(7), default="#2563EB")
    color_bot_bubble        = Column(String(7), default="#F3F4F6")
    font_family             = Column(String(100), default="Inter")
    font_size_base          = Column(Integer, default=14)
    border_radius           = Column(Integer, default=12)
    widget_width            = Column(Integer, default=380)
    widget_height           = Column(Integer, default=600)
    position                = Column(String(20), default="bottom-right")
    dark_mode_enabled       = Column(Boolean, default=False)
    dark_color_background   = Column(String(7), default="#1F2937")
    dark_color_text         = Column(String(7), default="#F9FAFB")
    custom_css              = Column(Text)
    rtl_enabled             = Column(Boolean, default=False)
    template_name           = Column(String(50), default="modern")
    # Widget branding & fallback contacts
    logo_url                = Column(Text)
    welcome_message         = Column(Text, default="Hello! How can I help you today?")
    fallback_whatsapp       = Column(String(30))
    fallback_email          = Column(String(255))
    fallback_phone          = Column(String(30))
    fallback_message        = Column(Text, default="Our team is here to help. Reach us via:")
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="theme")


class ChatbotPrechatForm(Base):
    __tablename__ = "chatbot_prechat_forms"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    is_enabled  = Column(Boolean, nullable=False, default=False)
    title       = Column(String(255), default="Before we start...")
    message     = Column(Text)
    fields      = Column(JSONB, nullable=False, default=list)
    remember_user = Column(Boolean, default=True)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    chatbot = relationship("Chatbot", back_populates="prechat_form")
