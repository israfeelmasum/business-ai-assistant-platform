"""
Chat module — SQLAlchemy ORM models.
Tables: end_users, conversations, messages, message_reactions,
        canned_responses, ai_decision_logs
"""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BigInteger,
    Numeric, Enum as SAEnum, ForeignKey, UniqueConstraint, ARRAY, Date
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from app.database import Base
import enum

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    from sqlalchemy import Text as Vector
    VECTOR_AVAILABLE = False


class ConversationStatus(str, enum.Enum):
    active              = "active"
    resolved            = "resolved"
    human_escalated     = "human_escalated"
    abandoned           = "abandoned"
    spam                = "spam"


class MessageRole(str, enum.Enum):
    user        = "user"
    assistant   = "assistant"
    system      = "system"
    agent       = "agent"


class MessageType(str, enum.Enum):
    text            = "text"
    image           = "image"
    file            = "file"
    voice           = "voice"
    form_submission = "form_submission"
    system_event    = "system_event"


class EscalationTrigger(str, enum.Enum):
    low_confidence  = "low_confidence"
    high_eil        = "high_eil"
    user_requested  = "user_requested"
    keyword_match   = "keyword_match"
    admin_manual    = "admin_manual"


class EscalationStatus(str, enum.Enum):
    pending     = "pending"
    active      = "active"
    resolved    = "resolved"
    timeout     = "timeout"


class EndUser(Base):
    """End-user identity across chat sessions (persistent cross-session profile)."""
    __tablename__ = "end_users"
    __table_args__ = (
        UniqueConstraint("org_id", "chatbot_id", "external_id", name="uq_end_users"),
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id                  = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id              = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id             = Column(String(255))  # device fingerprint / client user id
    name                    = Column(String(255))
    email                   = Column(String(255))
    phone                   = Column(String(30))
    language                = Column(String(10))
    timezone                = Column(String(100))
    extra_data                = Column("metadata", JSONB, default=dict)
    profile_embedding       = Column(Vector(768) if VECTOR_AVAILABLE else Text)
    profile_summary         = Column(Text)
    total_conversations     = Column(Integer, nullable=False, default=0)
    last_seen_at            = Column(DateTime(timezone=True))
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="end_user")


class Conversation(Base):
    __tablename__ = "conversations"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id          = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    end_user_id         = Column(UUID(as_uuid=True), ForeignKey("end_users.id", ondelete="SET NULL"), nullable=True)
    session_id          = Column(String(100), nullable=False, index=True)
    channel             = Column(SAEnum("web_widget", "mobile_sdk", "whatsapp", "telegram",
                                       "slack", "rest_api", "facebook",
                                       name="deployment_channel", create_type=False), nullable=False, default="web_widget")
    status              = Column(SAEnum(ConversationStatus, name="conversation_status"), nullable=False, default=ConversationStatus.active)
    language_detected   = Column(String(10))
    user_info           = Column(JSONB, default=dict)
    prechat_data        = Column(JSONB, default=dict)
    assigned_agent_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message_count       = Column(Integer, nullable=False, default=0)
    user_message_count  = Column(Integer, nullable=False, default=0)
    first_response_ms   = Column(Integer)
    resolved_at         = Column(DateTime(timezone=True))
    last_message_at     = Column(DateTime(timezone=True))
    extra_data            = Column("metadata", JSONB, default=dict)
    utm_source          = Column(String(100))
    utm_medium          = Column(String(100))
    referrer_url        = Column(Text)
    user_agent          = Column(Text)
    ip_address          = Column(INET)
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    end_user    = relationship("EndUser", back_populates="conversations")
    messages    = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                               order_by="Message.created_at")
    escalations = relationship("Escalation", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role            = Column(SAEnum(MessageRole, name="message_role"), nullable=False)
    type            = Column(SAEnum(MessageType, name="message_type"), nullable=False, default=MessageType.text)
    content         = Column(Text)
    attachments     = Column(JSONB, default=list)
    model_used      = Column(String(100))
    tokens_input    = Column(Integer)
    tokens_output   = Column(Integer)
    latency_ms      = Column(Integer)
    confidence      = Column(Numeric(4, 3))
    eil_score       = Column(Numeric(4, 3))
    intent          = Column(String(100))
    rag_sources     = Column(JSONB, default=list)
    suggestions     = Column(ARRAY(Text))
    action_data     = Column(JSONB)
    trace_id        = Column(UUID(as_uuid=True), default=uuid.uuid4)
    agent_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    conversation    = relationship("Conversation", back_populates="messages")
    reactions       = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")


class Escalation(Base):
    __tablename__ = "escalations"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id     = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger             = Column(SAEnum(EscalationTrigger, name="escalation_trigger"), nullable=False)
    trigger_details     = Column(JSONB, default=dict)
    status              = Column(SAEnum(EscalationStatus, name="escalation_status"), nullable=False, default=EscalationStatus.pending)
    assigned_agent_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at         = Column(DateTime(timezone=True))
    sla_minutes         = Column(Integer, default=30)
    sla_deadline        = Column(DateTime(timezone=True))
    resolved_at         = Column(DateTime(timezone=True))
    resolved_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes    = Column(Text)
    admin_notified_at   = Column(DateTime(timezone=True))
    admin_notified_via  = Column(String(50))
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="escalations")


class MessageReaction(Base):
    __tablename__ = "message_reactions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id  = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction    = Column(String(20), nullable=False)  # thumbs_up / thumbs_down / flag
    comment     = Column(Text)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    message = relationship("Message", back_populates="reactions")


class CannedResponse(Base):
    __tablename__ = "canned_responses"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id  = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=True)
    title       = Column(String(200), nullable=False)
    content     = Column(Text, nullable=False)
    tags        = Column(ARRAY(Text))
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AiDecisionLog(Base):
    """Full audit trail of every AI decision — for debugging + compliance."""
    __tablename__ = "ai_decision_logs"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id                = Column(UUID(as_uuid=True), nullable=False, index=True)
    message_id              = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    conversation_id         = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    chatbot_id              = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=True, index=True)
    org_id                  = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    system_prompt_snapshot  = Column(Text)
    retrieved_context       = Column(JSONB, default=list)
    user_message            = Column(Text)
    ai_response             = Column(Text)
    model_used              = Column(String(100))
    provider_type           = Column(String(50))
    tokens_input            = Column(Integer)
    tokens_output           = Column(Integer)
    confidence              = Column(Numeric(4, 3))
    eil_score               = Column(Numeric(4, 3))
    intent                  = Column(String(100))
    vector_search_ms        = Column(Integer)
    llm_ttft_ms             = Column(Integer)
    total_latency_ms        = Column(Integer)
    was_escalated           = Column(Boolean, default=False)
    was_hallucination_risk  = Column(Boolean, default=False)
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
