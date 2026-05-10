"""
Tokens module — repository layer.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tokens.models import (
    TokenPackage, TokenLedger, UsageRecord,
    TokenLedgerType, TokenAction
)


class TokenPackageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> List[TokenPackage]:
        result = await self.db.execute(
            select(TokenPackage)
            .where(TokenPackage.is_active == True)
            .order_by(TokenPackage.tokens)
        )
        return list(result.scalars().all())

    async def get_by_id(self, pkg_id: UUID) -> Optional[TokenPackage]:
        result = await self.db.execute(
            select(TokenPackage).where(TokenPackage.id == pkg_id)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, tokens: int, price, currency: str,
                     bonus_tokens: int = 0) -> TokenPackage:
        pkg = TokenPackage(
            name=name, tokens=tokens, price=price,
            currency=currency, bonus_tokens=bonus_tokens,
        )
        self.db.add(pkg)
        await self.db.flush()
        return pkg

    async def deactivate(self, pkg_id: UUID) -> None:
        await self.db.execute(
            update(TokenPackage)
            .where(TokenPackage.id == pkg_id)
            .values(is_active=False)
        )


class TokenLedgerRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, org_id: UUID) -> int:
        """Current balance = last balance_after in the ledger."""
        result = await self.db.execute(
            select(TokenLedger.balance_after)
            .where(TokenLedger.org_id == org_id)
            .order_by(TokenLedger.created_at.desc())
            .limit(1)
        )
        val = result.scalar_one_or_none()
        return val if val is not None else 0

    async def get_last_entry(self, org_id: UUID) -> Optional[TokenLedger]:
        result = await self.db.execute(
            select(TokenLedger)
            .where(TokenLedger.org_id == org_id)
            .order_by(TokenLedger.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def credit(
        self,
        org_id: UUID,
        action: TokenAction,
        tokens: int,
        chatbot_id: Optional[UUID] = None,
        reference_id: Optional[UUID] = None,
        model_used: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TokenLedger:
        current = await self.get_balance(org_id)
        balance_after = current + tokens
        entry = TokenLedger(
            org_id=org_id,
            chatbot_id=chatbot_id,
            type=TokenLedgerType.credit,
            action=action,
            tokens=tokens,
            balance_after=balance_after,
            reference_id=reference_id,
            model_used=model_used,
            metadata=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def debit(
        self,
        org_id: UUID,
        action: TokenAction,
        tokens: int,
        chatbot_id: Optional[UUID] = None,
        reference_id: Optional[UUID] = None,
        model_used: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TokenLedger:
        current = await self.get_balance(org_id)
        balance_after = current - tokens
        entry = TokenLedger(
            org_id=org_id,
            chatbot_id=chatbot_id,
            type=TokenLedgerType.debit,
            action=action,
            tokens=tokens,
            balance_after=balance_after,
            reference_id=reference_id,
            model_used=model_used,
            metadata=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_org_ledger(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TokenLedger]:
        result = await self.db.execute(
            select(TokenLedger)
            .where(TokenLedger.org_id == org_id)
            .order_by(TokenLedger.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class UsageRecordRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self,
        org_id: UUID,
        year: int,
        month: int,
        chatbot_id: Optional[UUID] = None,
    ) -> UsageRecord:
        result = await self.db.execute(
            select(UsageRecord).where(
                UsageRecord.org_id == org_id,
                UsageRecord.chatbot_id == chatbot_id,
                UsageRecord.period_year == year,
                UsageRecord.period_month == month,
            )
        )
        rec = result.scalar_one_or_none()
        if rec is None:
            rec = UsageRecord(
                org_id=org_id,
                chatbot_id=chatbot_id,
                period_year=year,
                period_month=month,
            )
            self.db.add(rec)
            await self.db.flush()
        return rec

    async def increment(
        self,
        org_id: UUID,
        year: int,
        month: int,
        chatbot_id: Optional[UUID] = None,
        *,
        messages: int = 0,
        tokens: int = 0,
        storage_bytes: int = 0,
        api_calls: int = 0,
        vision_calls: int = 0,
        tts_calls: int = 0,
        stt_calls: int = 0,
        translation_calls: int = 0,
    ) -> None:
        rec = await self.get_or_create(org_id, year, month, chatbot_id)
        rec.messages_count          += messages
        rec.tokens_used             += tokens
        rec.storage_bytes_used      += storage_bytes
        rec.api_calls_count         += api_calls
        rec.vision_calls_count      += vision_calls
        rec.tts_calls_count         += tts_calls
        rec.stt_calls_count         += stt_calls
        rec.translation_calls_count += translation_calls
        rec.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def get_period(
        self,
        org_id: UUID,
        year: int,
        month: int,
    ) -> List[UsageRecord]:
        result = await self.db.execute(
            select(UsageRecord).where(
                UsageRecord.org_id == org_id,
                UsageRecord.period_year == year,
                UsageRecord.period_month == month,
            )
        )
        return list(result.scalars().all())

    async def list_org_usage(self, org_id: UUID, limit: int = 12) -> List[UsageRecord]:
        result = await self.db.execute(
            select(UsageRecord)
            .where(UsageRecord.org_id == org_id)
            .order_by(
                UsageRecord.period_year.desc(),
                UsageRecord.period_month.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())
