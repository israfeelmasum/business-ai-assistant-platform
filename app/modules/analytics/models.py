"""
Analytics module — SQLAlchemy ORM models.

Tables:
  chatbot_analytics_daily — written by nightly aggregation / real-time increments
  analytics_reports       — AI-summarised period reports (weekly / monthly / yearly)
"""

import uuid
from datetime import datetime, date as DateType
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, BigInteger, Numeric, Date, Float, String, Text,
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ChatbotAnalyticsDaily(Base):
    __tablename__ = "chatbot_analytics_daily"
    __table_args__ = (UniqueConstraint("chatbot_id", "date", name="uq_analytics_chatbot_date"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id          = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    date                = Column(Date, nullable=False)
    # Volume
    total_conversations = Column(Integer, default=0)
    new_conversations   = Column(Integer, default=0)
    total_messages      = Column(Integer, default=0)
    # Quality
    avg_confidence      = Column(Numeric(4, 3))
    avg_eil_score       = Column(Numeric(4, 3))
    avg_response_ms     = Column(Integer)
    # Outcomes
    resolved_count      = Column(Integer, default=0)
    escalated_count     = Column(Integer, default=0)
    abandoned_count     = Column(Integer, default=0)
    # Users
    unique_users        = Column(Integer, default=0)
    returning_users     = Column(Integer, default=0)
    # Tokens
    tokens_used         = Column(BigInteger, default=0)


class AnalyticsReport(Base):
    """
    Stores AI-summarised analytics reports generated on demand.
    Unique per (org_id, period_type, period_label, chatbot_id).
    chatbot_id=NULL means the report covers the whole organisation.
    """
    __tablename__ = "analytics_reports"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "period_type", "period_label", "chatbot_id",
            name="uq_analytics_report_period",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id               = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    chatbot_id           = Column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="SET NULL"),
                                  nullable=True, index=True)
    period_type          = Column(String(20), nullable=False)   # weekly | monthly | yearly
    period_label         = Column(String(20), nullable=False)   # e.g. "2026-W15"
    period_start         = Column(Date, nullable=False)
    period_end           = Column(Date, nullable=False)
    # Core metrics
    total_conversations  = Column(Integer, default=0)
    total_messages       = Column(Integer, default=0)
    escalation_count     = Column(Integer, default=0)
    escalation_rate      = Column(Float, default=0.0)
    avg_confidence       = Column(Float, default=0.0)
    unique_users         = Column(Integer, default=0)
    # JSON detail
    top_questions        = Column(JSONB, default=list)
    staff_stats          = Column(JSONB, default=list)
    ai_summary           = Column(Text)
    generated_at         = Column(DateTime(timezone=True), default=datetime.utcnow)
