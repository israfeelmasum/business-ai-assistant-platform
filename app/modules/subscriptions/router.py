"""
Subscriptions router — plans, subscriptions, invoices, payments.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.subscriptions.schemas import (
    PlanResponse, SubscribeRequest, CancelSubscriptionRequest,
    SubscriptionResponse, InvoiceResponse, RecordPaymentRequest, PaymentResponse
)
from app.modules.subscriptions.service import SubscriptionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Subscriptions"])


# ── Public Plans ───────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all active plans (public — no auth required)."""
    svc = SubscriptionService(db)
    return await svc.list_plans()


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get plan details by ID."""
    svc = SubscriptionService(db)
    return await svc.get_plan(plan_id)


# ── Org Subscription ───────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current subscription for an organization."""
    svc = SubscriptionService(db)
    return await svc.get_subscription(org_id)


@router.post(
    "/organizations/{org_id}/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    org_id: UUID,
    req: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subscribe to a plan (or change plans). Admin only."""
    svc = SubscriptionService(db)
    return await svc.subscribe(org_id, req, requester_id=current_user.id)


@router.post("/organizations/{org_id}/subscription/cancel")
async def cancel_subscription(
    org_id: UUID,
    req: CancelSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel the organization's subscription. Admin only."""
    svc = SubscriptionService(db)
    return await svc.cancel_subscription(org_id, req, requester_id=current_user.id)


@router.post(
    "/organizations/{org_id}/subscription/reactivate",
    response_model=SubscriptionResponse,
)
async def reactivate_subscription(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a cancelled subscription. Admin only."""
    svc = SubscriptionService(db)
    return await svc.reactivate_subscription(org_id, requester_id=current_user.id)


# ── Invoices ───────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all invoices for the organization."""
    svc = SubscriptionService(db)
    return await svc.list_invoices(org_id, requester_id=current_user.id)


@router.get("/organizations/{org_id}/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    org_id: UUID,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific invoice."""
    svc = SubscriptionService(db)
    return await svc.get_invoice(org_id, invoice_id, requester_id=current_user.id)


# ── Payments ───────────────────────────────────────────────────────────────────

@router.post(
    "/organizations/{org_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    org_id: UUID,
    req: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually record a payment against an invoice (bKash, bank transfer, etc.). Admin only."""
    svc = SubscriptionService(db)
    return await svc.record_payment(org_id, req, processor_id=current_user.id)


@router.get("/organizations/{org_id}/payments", response_model=List[PaymentResponse])
async def list_payments(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all payments for the organization."""
    svc = SubscriptionService(db)
    return await svc.list_payments(org_id, requester_id=current_user.id)
