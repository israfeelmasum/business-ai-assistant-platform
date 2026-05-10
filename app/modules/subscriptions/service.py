"""
Subscriptions module — business logic.
Handles plan upgrades, downgrades, trial setup, billing periods, invoice generation.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscriptions.models import (
    Plan, Subscription, Invoice, Payment,
    PlanSlug, SubscriptionStatus, PaymentStatus
)
from app.modules.subscriptions.repository import (
    PlanRepository, SubscriptionRepository, InvoiceRepository, PaymentRepository
)
from app.modules.subscriptions.schemas import (
    PlanResponse, SubscriptionResponse, InvoiceResponse, PaymentResponse,
    SubscribeRequest, CancelSubscriptionRequest, RecordPaymentRequest
)
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)

# Free plan gets a 14-day trial
FREE_TRIAL_DAYS = 14
MONTHLY_DAYS    = 30
ANNUAL_DAYS     = 365


class SubscriptionService:

    def __init__(self, db: AsyncSession):
        self.db       = db
        self.plans    = PlanRepository(db)
        self.subs     = SubscriptionRepository(db)
        self.invoices = InvoiceRepository(db)
        self.payments = PaymentRepository(db)
        self.members  = MemberRepository(db)

    # ── Plans ──────────────────────────────────────────────────────────────────

    async def list_plans(self) -> List[PlanResponse]:
        plans = await self.plans.get_all_active()
        return [PlanResponse.model_validate(p) for p in plans]

    async def get_plan(self, plan_id: UUID) -> PlanResponse:
        plan = await self.plans.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Plan not found")
        return PlanResponse.model_validate(plan)

    # ── Subscription ───────────────────────────────────────────────────────────

    async def get_subscription(self, org_id: UUID) -> SubscriptionResponse:
        sub = await self.subs.get_by_org(org_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found. Subscribe to a plan first."
            )
        return SubscriptionResponse.model_validate(sub)

    async def subscribe(
        self, org_id: UUID, req: SubscribeRequest, requester_id: UUID
    ) -> SubscriptionResponse:
        await self._require_admin(org_id, requester_id)

        plan = await self.plans.get_by_slug(req.plan_slug)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Plan not available")

        now = datetime.now(timezone.utc)
        days = ANNUAL_DAYS if req.billing_cycle == "annual" else MONTHLY_DAYS
        period_end = now + timedelta(days=days)

        # Trial for free plan
        trial_ends_at = None
        sub_status = SubscriptionStatus.active
        if req.plan_slug == PlanSlug.free:
            trial_ends_at = now + timedelta(days=FREE_TRIAL_DAYS)
            sub_status = SubscriptionStatus.trialing

        existing = await self.subs.get_by_org(org_id)

        if existing:
            # Upgrade/downgrade — update in place
            await self.subs.update_plan(
                sub_id=existing.id,
                plan_id=plan.id,
                billing_cycle=req.billing_cycle,
                period_start=now,
                period_end=period_end,
                status=sub_status,
            )
            await self.db.commit()
            sub = await self.subs.get_by_org(org_id)
            logger.info(f"Subscription changed to {plan.slug} for org={org_id}")
        else:
            # New subscription
            sub = await self.subs.create(
                org_id=org_id,
                plan_id=plan.id,
                billing_cycle=req.billing_cycle,
                period_start=now,
                period_end=period_end,
                trial_ends_at=trial_ends_at,
                status=sub_status,
            )
            await self.db.commit()
            sub = await self.subs.get_by_org(org_id)
            logger.info(f"New subscription created: {plan.slug} for org={org_id}")

        # Auto-generate invoice for paid plans
        if plan.price_monthly > 0 or plan.price_annual > 0:
            price = plan.price_annual if req.billing_cycle == "annual" else plan.price_monthly
            inv = await self.invoices.create(
                org_id=org_id,
                amount=price,
                subscription_id=sub.id,
                line_items=[{
                    "description": f"{plan.name} — {req.billing_cycle}",
                    "amount": str(price),
                    "currency": "USD",
                }],
                due_date=now + timedelta(days=7),
            )
            await self.db.commit()
            logger.info(f"Invoice {inv.invoice_number} generated for org={org_id}")

        return SubscriptionResponse.model_validate(sub)

    async def cancel_subscription(
        self, org_id: UUID, req: CancelSubscriptionRequest, requester_id: UUID
    ) -> dict:
        await self._require_admin(org_id, requester_id)
        sub = await self._get_sub_or_404(org_id)

        if sub.status == SubscriptionStatus.cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is already cancelled"
            )

        await self.subs.cancel(sub.id, req.cancel_reason)
        await self.db.commit()
        logger.info(f"Subscription cancelled for org={org_id}")
        return {"message": "Subscription cancelled. Access continues until end of billing period."}

    async def reactivate_subscription(
        self, org_id: UUID, requester_id: UUID
    ) -> SubscriptionResponse:
        await self._require_admin(org_id, requester_id)
        sub = await self._get_sub_or_404(org_id)

        if sub.status != SubscriptionStatus.cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not cancelled"
            )

        days = ANNUAL_DAYS if sub.billing_cycle == "annual" else MONTHLY_DAYS
        period_end = datetime.now(timezone.utc) + timedelta(days=days)
        await self.subs.reactivate(sub.id, period_end)
        await self.db.commit()

        updated = await self.subs.get_by_org(org_id)
        return SubscriptionResponse.model_validate(updated)

    # ── Invoices ───────────────────────────────────────────────────────────────

    async def list_invoices(self, org_id: UUID, requester_id: UUID) -> List[InvoiceResponse]:
        await self._require_member(org_id, requester_id)
        invoices = await self.invoices.list_org_invoices(org_id)
        return [InvoiceResponse.model_validate(inv) for inv in invoices]

    async def get_invoice(
        self, org_id: UUID, invoice_id: UUID, requester_id: UUID
    ) -> InvoiceResponse:
        await self._require_member(org_id, requester_id)
        inv = await self.invoices.get_by_id(invoice_id)
        if not inv or inv.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Invoice not found")
        return InvoiceResponse.model_validate(inv)

    # ── Payments ───────────────────────────────────────────────────────────────

    async def record_payment(
        self, org_id: UUID, req: RecordPaymentRequest, processor_id: UUID
    ) -> PaymentResponse:
        """Manually record a payment (for BD gateways, bank transfer, etc.)."""
        await self._require_admin(org_id, processor_id)

        inv = await self.invoices.get_by_id(req.invoice_id)
        if not inv or inv.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Invoice not found")
        if inv.status == PaymentStatus.completed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Invoice already paid")

        pmt = await self.payments.create(
            org_id=org_id,
            invoice_id=req.invoice_id,
            gateway=req.gateway,
            amount=req.amount,
            currency=req.currency,
            gateway_txn_id=req.gateway_txn_id,
            payment_proof_url=req.payment_proof_url,
            payer_name=req.payer_name,
            payer_email=req.payer_email,
            payer_phone=req.payer_phone,
            notes=req.notes,
            processed_by=processor_id,
            status=PaymentStatus.completed,
        )
        # Mark invoice paid
        await self.invoices.mark_paid(req.invoice_id)
        # Activate subscription if it's pending payment
        sub = await self.subs.get_by_org(org_id)
        if sub and sub.status in (SubscriptionStatus.past_due, SubscriptionStatus.trialing):
            days = ANNUAL_DAYS if sub.billing_cycle == "annual" else MONTHLY_DAYS
            period_end = datetime.now(timezone.utc) + timedelta(days=days)
            await self.subs.reactivate(sub.id, period_end)

        await self.db.commit()
        logger.info(f"Payment recorded: {pmt.id} for invoice={req.invoice_id}, org={org_id}")
        return PaymentResponse.model_validate(pmt)

    async def list_payments(self, org_id: UUID, requester_id: UUID) -> List[PaymentResponse]:
        await self._require_member(org_id, requester_id)
        payments = await self.payments.list_org_payments(org_id)
        return [PaymentResponse.model_validate(p) for p in payments]

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_sub_or_404(self, org_id: UUID) -> Subscription:
        sub = await self.subs.get_by_org(org_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No subscription found for this organization")
        return sub

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")

    async def _require_admin(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
        if member.role not in ("admin",):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admin role required")
