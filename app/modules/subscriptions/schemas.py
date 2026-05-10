"""
Subscriptions module — Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.subscriptions.models import (
    PlanSlug, SubscriptionStatus, PaymentStatus, PaymentGateway
)


# ── Plans ──────────────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     UUID
    name:                   str
    slug:                   PlanSlug
    description:            Optional[str]
    price_monthly:          Decimal
    price_annual:           Decimal
    max_chatbots:           Optional[int]
    max_messages_per_month: Optional[int]
    max_tokens_per_month:   Optional[int]
    max_team_members:       Optional[int]
    max_knowledge_mb:       Optional[int]
    max_documents:          Optional[int]
    max_api_calls_per_day:  Optional[int]
    max_concurrent_users:   Optional[int]
    max_agent_seats:        Optional[int]
    features:               Dict[str, Any]
    is_active:              bool
    sort_order:             int


# ── Subscriptions ──────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    """Create or change a subscription."""
    plan_slug:      PlanSlug
    billing_cycle:  str = "monthly"  # monthly | annual

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, v: str) -> str:
        if v not in ("monthly", "annual"):
            raise ValueError("billing_cycle must be 'monthly' or 'annual'")
        return v


class CancelSubscriptionRequest(BaseModel):
    cancel_reason: Optional[str] = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                         UUID
    org_id:                     UUID
    plan_id:                    UUID
    status:                     SubscriptionStatus
    billing_cycle:              str
    current_period_start:       datetime
    current_period_end:         datetime
    trial_ends_at:              Optional[datetime]
    cancelled_at:               Optional[datetime]
    cancel_reason:              Optional[str]
    external_subscription_id:   Optional[str]
    created_at:                 datetime
    updated_at:                 datetime
    # Nested
    plan:                       Optional[PlanResponse] = None


# ── Invoices ───────────────────────────────────────────────────────────────────

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    org_id:         UUID
    subscription_id: Optional[UUID]
    invoice_number: str
    amount:         Decimal
    currency:       str
    status:         PaymentStatus
    due_date:       Optional[datetime]
    paid_at:        Optional[datetime]
    pdf_url:        Optional[str]
    line_items:     List[Any]
    notes:          Optional[str]
    created_at:     datetime
    updated_at:     datetime


# ── Payments ───────────────────────────────────────────────────────────────────

class RecordPaymentRequest(BaseModel):
    """Manually record a payment (e.g., bKash, bank transfer)."""
    invoice_id:         UUID
    gateway:            PaymentGateway
    amount:             Decimal
    currency:           str = "USD"
    gateway_txn_id:     Optional[str] = None
    payment_proof_url:  Optional[str] = None
    payer_name:         Optional[str] = None
    payer_email:        Optional[str] = None
    payer_phone:        Optional[str] = None
    notes:              Optional[str] = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    org_id:             UUID
    invoice_id:         Optional[UUID]
    gateway:            PaymentGateway
    amount:             Decimal
    currency:           str
    status:             PaymentStatus
    gateway_txn_id:     Optional[str]
    payment_proof_url:  Optional[str]
    payer_name:         Optional[str]
    payer_email:        Optional[str]
    payer_phone:        Optional[str]
    notes:              Optional[str]
    processed_at:       Optional[datetime]
    created_at:         datetime
