"""
Subscriptions module — repository layer (DB queries only, no business logic).
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.subscriptions.models import (
    Plan, Subscription, Invoice, Payment,
    PlanSlug, SubscriptionStatus, PaymentStatus, PaymentGateway
)


class PlanRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> List[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, plan_id: UUID) -> Optional[Plan]:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: PlanSlug) -> Optional[Plan]:
        result = await self.db.execute(select(Plan).where(Plan.slug == slug))
        return result.scalar_one_or_none()


class SubscriptionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_org(self, org_id: UUID) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.org_id == org_id)
            .options(selectinload(Subscription.plan))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, sub_id: UUID) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.id == sub_id)
            .options(selectinload(Subscription.plan))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        org_id: UUID,
        plan_id: UUID,
        billing_cycle: str,
        period_start: datetime,
        period_end: datetime,
        trial_ends_at: Optional[datetime] = None,
        status: SubscriptionStatus = SubscriptionStatus.trialing,
    ) -> Subscription:
        sub = Subscription(
            org_id=org_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_ends_at=trial_ends_at,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def update_plan(
        self,
        sub_id: UUID,
        plan_id: UUID,
        billing_cycle: str,
        period_start: datetime,
        period_end: datetime,
        status: SubscriptionStatus,
    ) -> None:
        await self.db.execute(
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(
                plan_id=plan_id,
                billing_cycle=billing_cycle,
                current_period_start=period_start,
                current_period_end=period_end,
                status=status,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def cancel(self, sub_id: UUID, reason: Optional[str]) -> None:
        await self.db.execute(
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(
                status=SubscriptionStatus.cancelled,
                cancelled_at=datetime.now(timezone.utc),
                cancel_reason=reason,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def reactivate(self, sub_id: UUID, period_end: datetime) -> None:
        await self.db.execute(
            update(Subscription)
            .where(Subscription.id == sub_id)
            .values(
                status=SubscriptionStatus.active,
                cancelled_at=None,
                cancel_reason=None,
                current_period_end=period_end,
                updated_at=datetime.now(timezone.utc),
            )
        )


class InvoiceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    def _next_invoice_number(self) -> str:
        ts = datetime.now(timezone.utc)
        rand = uuid.uuid4().hex[:6].upper()
        return f"INV-{ts.strftime('%Y%m')}-{rand}"

    async def create(
        self,
        org_id: UUID,
        amount,
        currency: str = "USD",
        subscription_id: Optional[UUID] = None,
        line_items: Optional[list] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> Invoice:
        inv = Invoice(
            org_id=org_id,
            subscription_id=subscription_id,
            invoice_number=self._next_invoice_number(),
            amount=amount,
            currency=currency,
            line_items=line_items or [],
            due_date=due_date,
            notes=notes,
        )
        self.db.add(inv)
        await self.db.flush()
        return inv

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_org_invoices(self, org_id: UUID) -> List[Invoice]:
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.org_id == org_id)
            .order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_paid(self, invoice_id: UUID) -> None:
        await self.db.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                status=PaymentStatus.completed,
                paid_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )


class PaymentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        org_id: UUID,
        invoice_id: Optional[UUID],
        gateway: PaymentGateway,
        amount,
        currency: str = "USD",
        gateway_txn_id: Optional[str] = None,
        payment_proof_url: Optional[str] = None,
        payer_name: Optional[str] = None,
        payer_email: Optional[str] = None,
        payer_phone: Optional[str] = None,
        notes: Optional[str] = None,
        processed_by: Optional[UUID] = None,
        status: PaymentStatus = PaymentStatus.completed,
    ) -> Payment:
        pmt = Payment(
            org_id=org_id,
            invoice_id=invoice_id,
            gateway=gateway,
            amount=amount,
            currency=currency,
            status=status,
            gateway_txn_id=gateway_txn_id,
            payment_proof_url=payment_proof_url,
            payer_name=payer_name,
            payer_email=payer_email,
            payer_phone=payer_phone,
            notes=notes,
            processed_by=processed_by,
            processed_at=datetime.now(timezone.utc) if status == PaymentStatus.completed else None,
        )
        self.db.add(pmt)
        await self.db.flush()
        return pmt

    async def list_org_payments(self, org_id: UUID) -> List[Payment]:
        result = await self.db.execute(
            select(Payment)
            .where(Payment.org_id == org_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())
