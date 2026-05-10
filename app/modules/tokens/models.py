"""
Tokens module — SQLAlchemy ORM models.
Tables: token_packages, token_ledger, usage_records
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, BigInteger,
    Numeric, Enum as SAEnum, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TokenLedgerType(str, enum.Enum):
    credit  = "credit"
    debit   = "debit"


class TokenAction(str, enum.Enum):
    chat_message    = "chat_message"
    embedding       = "embedding"
    vision          = "vision"
    tts             = "tts"
    stt             = "stt"
    translation     = "translation"
    top_up          = "top_up"
    plan_credit     = "plan_credit"
    refund          = "refund"


class TokenPackage(Base):
    __tablename__ = "token_packages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(100), nullable=False)
    tokens          = Column(BigInteger, nullable=False)
    price           = Column(Numeric(10, 2), nullable=False)
    currency        = Column(String(3), nullable=False, default="USD")
    bonus_tokens    = Column(BigInteger, nullable=False, default=0)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TokenLedger(Base):
    __tablename__ = "token_ledger"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id      = Column(UUID(as_uuid=True), nullable=True, index=True)  # FK added with chatbots module
    type            = Column(SAEnum(TokenLedgerType, name="token_ledger_type"), nullable=False)
    action          = Column(SAEnum(TokenAction, name="token_action"), nullable=False)
    tokens          = Column(BigInteger, nullable=False)
    balance_after   = Column(BigInteger, nullable=False)
    reference_id    = Column(UUID(as_uuid=True))
    model_used      = Column(String(100))
    extra_data        = Column("metadata", JSONB, default=dict)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("org_id", "chatbot_id", "period_year", "period_month",
                         name="uq_usage_records"),
    )

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id                      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id                  = Column(UUID(as_uuid=True), nullable=True, index=True)  # FK added with chatbots module
    period_year                 = Column(Integer, nullable=False)
    period_month                = Column(Integer, nullable=False)
    messages_count              = Column(BigInteger, nullable=False, default=0)
    tokens_used                 = Column(BigInteger, nullable=False, default=0)
    storage_bytes_used          = Column(BigInteger, nullable=False, default=0)
    api_calls_count             = Column(BigInteger, nullable=False, default=0)
    vision_calls_count          = Column(BigInteger, nullable=False, default=0)
    tts_calls_count             = Column(BigInteger, nullable=False, default=0)
    stt_calls_count             = Column(BigInteger, nullable=False, default=0)
    translation_calls_count     = Column(BigInteger, nullable=False, default=0)
    unique_users_count          = Column(Integer, nullable=False, default=0)
    escalations_count           = Column(Integer, nullable=False, default=0)
    updated_at                  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
