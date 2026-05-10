"""
Subscriptions module — SQLAlchemy ORM models.
Tables: plans, subscriptions, invoices, payments
"""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BigInteger,
    Numeric, Enum as SAEnum, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class PlanSlug(str, enum.Enum):
    free            = "free"
    starter         = "starter"
    professional    = "professional"
    enterprise      = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    trialing    = "trialing"
    active      = "active"
    past_due    = "past_due"
    cancelled   = "cancelled"
    paused      = "paused"


class PaymentStatus(str, enum.Enum):
    pending     = "pending"
    processing  = "processing"
    completed   = "completed"
    failed      = "failed"
    refunded    = "refunded"


class PaymentGateway(str, enum.Enum):
    sslcommerz      = "sslcommerz"
    bkash           = "bkash"
    nagad           = "nagad"
    rocket          = "rocket"
    stripe          = "stripe"
    paypal          = "paypal"
    zelle           = "zelle"
    bank_transfer   = "bank_transfer"
    manual          = "manual"


class Plan(Base):
    __tablename__ = "plans"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                    = Column(String(100), nullable=False)
    slug                    = Column(SAEnum(PlanSlug, name="plan_slug"), nullable=False, unique=True)
    description             = Column(Text)
    price_monthly           = Column(Numeric(10, 2), nullable=False, default=0)
    price_annual            = Column(Numeric(10, 2), nullable=False, default=0)
    # Limits — NULL means unlimited
    max_chatbots            = Column(Integer)
    max_messages_per_month  = Column(Integer)
    max_tokens_per_month    = Column(BigInteger)
    max_team_members        = Column(Integer)
    max_knowledge_mb        = Column(Integer)
    max_documents           = Column(Integer)
    max_api_calls_per_day   = Column(Integer)
    max_concurrent_users    = Column(Integer)
    max_agent_seats         = Column(Integer)
    # Feature flags
    features                = Column(JSONB, nullable=False, default=dict)
    is_active               = Column(Boolean, nullable=False, default=True)
    sort_order              = Column(Integer, nullable=False, default=0)
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("org_id", name="uq_subscriptions_org"),)

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id                      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id                     = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status                      = Column(SAEnum(SubscriptionStatus, name="subscription_status"), nullable=False, default=SubscriptionStatus.trialing)
    billing_cycle               = Column(String(10), nullable=False, default="monthly")  # monthly | annual
    current_period_start        = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    current_period_end          = Column(DateTime(timezone=True), nullable=False)
    trial_ends_at               = Column(DateTime(timezone=True))
    cancelled_at                = Column(DateTime(timezone=True))
    cancel_reason               = Column(Text)
    external_subscription_id    = Column(String(255))
    extra_data                    = Column("metadata", JSONB, default=dict)
    created_at                  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at                  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    organization    = relationship("Organization", back_populates="subscription")
    plan            = relationship("Plan", back_populates="subscriptions")
    invoices        = relationship("Invoice", back_populates="subscription")


class Invoice(Base):
    __tablename__ = "invoices"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    invoice_number  = Column(String(50), nullable=False, unique=True)
    amount          = Column(Numeric(10, 2), nullable=False)
    currency        = Column(String(3), nullable=False, default="USD")
    status          = Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.pending)
    due_date        = Column(DateTime(timezone=True))
    paid_at         = Column(DateTime(timezone=True))
    pdf_url         = Column(Text)
    line_items      = Column(JSONB, nullable=False, default=list)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    subscription    = relationship("Subscription", back_populates="invoices")
    payments        = relationship("Payment", back_populates="invoice")


class Payment(Base):
    __tablename__ = "payments"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id              = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id          = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    gateway             = Column(SAEnum(PaymentGateway, name="payment_gateway"), nullable=False)
    amount              = Column(Numeric(10, 2), nullable=False)
    currency            = Column(String(3), nullable=False, default="USD")
    status              = Column(SAEnum(PaymentStatus, name="payment_status", create_type=False), nullable=False, default=PaymentStatus.pending)
    gateway_txn_id      = Column(String(255))
    gateway_response    = Column(JSONB, default=dict)
    payment_proof_url   = Column(Text)
    payer_name          = Column(String(255))
    payer_email         = Column(String(255))
    payer_phone         = Column(String(30))
    notes               = Column(Text)
    processed_by        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    processed_at        = Column(DateTime(timezone=True))
    created_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
