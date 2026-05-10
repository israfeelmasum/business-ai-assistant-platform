"""
Tokens module — business logic.
Handles token balances, top-ups, quota checking, usage metering.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tokens.models import TokenAction, TokenLedger, UsageRecord
from app.modules.tokens.repository import (
    TokenPackageRepository, TokenLedgerRepository, UsageRecordRepository
)
from app.modules.tokens.schemas import (
    TokenPackageResponse, TokenLedgerEntry, OrgTokenBalance,
    UsageRecordResponse, CreateTokenPackageRequest, DebitTokensRequest
)
from app.modules.organizations.repository import MemberRepository
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.models import SubscriptionStatus

logger = logging.getLogger(__name__)

# ── Per-action token costs ─────────────────────────────────────────────────────
# These are platform defaults. Orgs using BYOK still consume platform tokens
# for metering; cost values are informational for the token ledger.
TOKEN_COSTS: dict[TokenAction, int] = {
    TokenAction.chat_message:   10,     # per LLM request
    TokenAction.embedding:      2,      # per chunk embed
    TokenAction.vision:         50,     # per image analysis
    TokenAction.tts:            20,     # per TTS request
    TokenAction.stt:            20,     # per STT request
    TokenAction.translation:    5,      # per translation call
}


class TokenService:

    def __init__(self, db: AsyncSession):
        self.db       = db
        self.packages = TokenPackageRepository(db)
        self.ledger   = TokenLedgerRepository(db)
        self.usage    = UsageRecordRepository(db)
        self.members  = MemberRepository(db)
        self.subs     = SubscriptionRepository(db)

    # ── Token Packages ─────────────────────────────────────────────────────────

    async def list_packages(self) -> List[TokenPackageResponse]:
        pkgs = await self.packages.get_all_active()
        return [TokenPackageResponse.model_validate(p) for p in pkgs]

    async def create_package(
        self, req: CreateTokenPackageRequest
    ) -> TokenPackageResponse:
        pkg = await self.packages.create(
            name=req.name, tokens=req.tokens, price=req.price,
            currency=req.currency, bonus_tokens=req.bonus_tokens,
        )
        await self.db.commit()
        await self.db.refresh(pkg)
        return TokenPackageResponse.model_validate(pkg)

    async def deactivate_package(self, pkg_id: UUID) -> None:
        await self.packages.deactivate(pkg_id)
        await self.db.commit()

    # ── Balance ────────────────────────────────────────────────────────────────

    async def get_balance(self, org_id: UUID, requester_id: UUID) -> OrgTokenBalance:
        await self._require_member(org_id, requester_id)
        balance = await self.ledger.get_balance(org_id)
        last = await self.ledger.get_last_entry(org_id)
        return OrgTokenBalance(
            org_id=org_id,
            balance=balance,
            last_updated=last.created_at if last else None,
        )

    # ── Top-up ─────────────────────────────────────────────────────────────────

    async def apply_top_up(
        self,
        org_id: UUID,
        pkg_id: UUID,
        reference_id: Optional[UUID] = None,
    ) -> TokenLedgerEntry:
        """Called after payment is confirmed. Credits tokens from a package."""
        pkg = await self.packages.get_by_id(pkg_id)
        if not pkg or not pkg.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Token package not found")

        total = pkg.tokens + pkg.bonus_tokens
        entry = await self.ledger.credit(
            org_id=org_id,
            action=TokenAction.top_up,
            tokens=total,
            reference_id=reference_id,
            metadata={"package_id": str(pkg_id), "package_name": pkg.name},
        )
        await self.db.commit()
        logger.info(f"Top-up: +{total} tokens for org={org_id} (pkg={pkg.name})")
        return TokenLedgerEntry.model_validate(entry)

    async def apply_plan_credit(
        self,
        org_id: UUID,
        tokens: int,
        reference_id: Optional[UUID] = None,
    ) -> TokenLedgerEntry:
        """Called at subscription renewal to credit plan quota tokens."""
        entry = await self.ledger.credit(
            org_id=org_id,
            action=TokenAction.plan_credit,
            tokens=tokens,
            reference_id=reference_id,
            metadata={"source": "plan_renewal"},
        )
        await self.db.commit()
        logger.info(f"Plan credit: +{tokens} tokens for org={org_id}")
        return TokenLedgerEntry.model_validate(entry)

    # ── Debit (called internally by Chat Engine, RAG, etc.) ───────────────────

    async def debit_tokens(
        self,
        org_id: UUID,
        req: DebitTokensRequest,
    ) -> TokenLedgerEntry:
        """
        Debit tokens for an AI action. Raises 402 if insufficient balance.
        This is an internal method — called by other services, not directly via API.
        """
        cost = req.tokens if req.tokens > 0 else TOKEN_COSTS.get(req.action, 1)

        balance = await self.ledger.get_balance(org_id)
        if balance < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient token balance. Required: {cost}, Available: {balance}. "
                       "Please top up your token balance."
            )

        entry = await self.ledger.debit(
            org_id=org_id,
            action=req.action,
            tokens=cost,
            chatbot_id=req.chatbot_id,
            reference_id=req.reference_id,
            model_used=req.model_used,
            metadata=req.metadata,
        )

        # Update usage record for current month
        now = datetime.now(timezone.utc)
        await self.usage.increment(
            org_id=org_id,
            year=now.year,
            month=now.month,
            chatbot_id=req.chatbot_id,
            tokens=cost,
            messages=1 if req.action == TokenAction.chat_message else 0,
            vision_calls=1 if req.action == TokenAction.vision else 0,
            tts_calls=1 if req.action == TokenAction.tts else 0,
            stt_calls=1 if req.action == TokenAction.stt else 0,
            translation_calls=1 if req.action == TokenAction.translation else 0,
        )

        return TokenLedgerEntry.model_validate(entry)

    # ── Ledger History ─────────────────────────────────────────────────────────

    async def get_ledger(
        self, org_id: UUID, requester_id: UUID,
        limit: int = 100, offset: int = 0
    ) -> List[TokenLedgerEntry]:
        await self._require_member(org_id, requester_id)
        entries = await self.ledger.list_org_ledger(org_id, limit=limit, offset=offset)
        return [TokenLedgerEntry.model_validate(e) for e in entries]

    # ── Usage Records ──────────────────────────────────────────────────────────

    async def get_usage(
        self, org_id: UUID, requester_id: UUID, limit: int = 12
    ) -> List[UsageRecordResponse]:
        await self._require_member(org_id, requester_id)
        records = await self.usage.list_org_usage(org_id, limit=limit)
        return [UsageRecordResponse.model_validate(r) for r in records]

    async def get_current_usage(
        self, org_id: UUID, requester_id: UUID
    ) -> List[UsageRecordResponse]:
        await self._require_member(org_id, requester_id)
        now = datetime.now(timezone.utc)
        records = await self.usage.get_period(org_id, now.year, now.month)
        return [UsageRecordResponse.model_validate(r) for r in records]

    # ── Quota Check (called by Chat Engine before processing) ─────────────────

    async def check_quota(self, org_id: UUID, action: TokenAction) -> bool:
        """
        Returns True if org has enough tokens for the action.
        Also checks subscription plan limits for message quota.
        """
        cost = TOKEN_COSTS.get(action, 1)
        balance = await self.ledger.get_balance(org_id)
        if balance < cost:
            return False

        # Also check plan message quota for chat messages
        if action == TokenAction.chat_message:
            sub = await self.subs.get_by_org(org_id)
            if sub and sub.status == SubscriptionStatus.active:
                plan = sub.plan
                if plan.max_messages_per_month is not None:
                    now = datetime.now(timezone.utc)
                    records = await self.usage.get_period(org_id, now.year, now.month)
                    total_msgs = sum(r.messages_count for r in records)
                    if total_msgs >= plan.max_messages_per_month:
                        return False

        return True

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
