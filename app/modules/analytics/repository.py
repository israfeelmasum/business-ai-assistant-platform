"""
Analytics module — repository layer.
All queries use raw SQL aggregations for performance.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import ChatbotAnalyticsDaily
from app.modules.chat.models import (
    Conversation, Message, Escalation,
    ConversationStatus, EscalationStatus
)
from app.modules.tokens.models import TokenLedger, TokenLedgerType, UsageRecord


class AnalyticsRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Dashboard Stats (live) ─────────────────────────────────────────────────

    async def get_conversation_stats(
        self, org_id: UUID, start: date, end: date,
        chatbot_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Aggregate conversation stats for a date range."""
        q = (
            select(
                func.count(Conversation.id).label("total"),
                func.sum(case((Conversation.status == ConversationStatus.active, 1), else_=0)).label("active"),
                func.sum(case((Conversation.status == ConversationStatus.resolved, 1), else_=0)).label("resolved"),
                func.sum(case((Conversation.status == ConversationStatus.human_escalated, 1), else_=0)).label("escalated"),
                func.avg(Conversation.message_count).label("avg_messages"),
            )
            .where(
                Conversation.org_id == org_id,
                func.date(Conversation.created_at) >= start,
                func.date(Conversation.created_at) <= end,
            )
        )
        if chatbot_id:
            q = q.where(Conversation.chatbot_id == chatbot_id)

        result = await self.db.execute(q)
        row = result.one()
        return {
            "total_conversations":          row.total or 0,
            "active_conversations":         int(row.active or 0),
            "resolved_conversations":       int(row.resolved or 0),
            "escalated_conversations":      int(row.escalated or 0),
            "avg_messages_per_conversation": float(row.avg_messages or 0),
        }

    async def get_message_stats(
        self, org_id: UUID, start: date, end: date,
        chatbot_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        q = (
            select(
                func.count(Message.id).label("total"),
                func.avg(Message.latency_ms).label("avg_latency"),
                func.avg(Message.confidence).label("avg_confidence"),
                func.avg(Message.eil_score).label("avg_eil"),
            )
            .where(
                Message.org_id == org_id,
                func.date(Message.created_at) >= start,
                func.date(Message.created_at) <= end,
            )
        )
        if chatbot_id:
            q = q.join(Conversation, Conversation.id == Message.conversation_id)
            q = q.where(Conversation.chatbot_id == chatbot_id)

        result = await self.db.execute(q)
        row = result.one()
        return {
            "total_messages":   row.total or 0,
            "avg_response_ms":  int(row.avg_latency) if row.avg_latency else None,
            "avg_confidence":   float(row.avg_confidence) if row.avg_confidence else None,
            "avg_eil_score":    float(row.avg_eil) if row.avg_eil else None,
        }

    async def get_unique_users(
        self, org_id: UUID, start: date, end: date,
        chatbot_id: Optional[UUID] = None,
    ) -> int:
        q = (
            select(func.count(func.distinct(Conversation.end_user_id)))
            .where(
                Conversation.org_id == org_id,
                Conversation.end_user_id.isnot(None),
                func.date(Conversation.created_at) >= start,
                func.date(Conversation.created_at) <= end,
            )
        )
        if chatbot_id:
            q = q.where(Conversation.chatbot_id == chatbot_id)
        result = await self.db.execute(q)
        return result.scalar() or 0

    async def get_escalation_counts(self, org_id: UUID) -> Dict[str, int]:
        pending = await self.db.execute(
            select(func.count(Escalation.id)).where(
                Escalation.org_id == org_id,
                Escalation.status == EscalationStatus.pending,
            )
        )
        now = datetime.now(timezone.utc)
        overdue = await self.db.execute(
            select(func.count(Escalation.id)).where(
                Escalation.org_id == org_id,
                Escalation.status.in_([EscalationStatus.pending, EscalationStatus.active]),
                Escalation.sla_deadline <= now,
            )
        )
        return {
            "pending_escalations": pending.scalar() or 0,
            "overdue_escalations": overdue.scalar() or 0,
        }

    async def get_token_totals(
        self, org_id: UUID, start: date, end: date,
    ) -> Dict[str, Any]:
        q = (
            select(
                func.sum(TokenLedger.tokens).label("total_used"),
            )
            .where(
                TokenLedger.org_id == org_id,
                TokenLedger.type == TokenLedgerType.debit,
                func.date(TokenLedger.created_at) >= start,
                func.date(TokenLedger.created_at) <= end,
            )
        )
        result = await self.db.execute(q)
        row = result.one()
        total_used = int(row.total_used or 0)
        # Very rough cost estimate: $0.000002 per token (Ollama/self-hosted = $0)
        cost_usd = total_used * 0.000002
        return {"total_tokens_used": total_used, "estimated_cost_usd": cost_usd}

    # ── Per-chatbot breakdown ──────────────────────────────────────────────────

    async def get_chatbot_breakdown(
        self, org_id: UUID, start: date, end: date,
    ) -> List[Dict[str, Any]]:
        """Per-chatbot conversation + message stats."""
        result = await self.db.execute(
            select(
                Conversation.chatbot_id,
                func.count(Conversation.id).label("total_conversations"),
                func.sum(Conversation.message_count).label("total_messages"),
                func.sum(case((Conversation.status == ConversationStatus.resolved, 1), else_=0)).label("resolved_count"),
                func.sum(case((Conversation.status == ConversationStatus.human_escalated, 1), else_=0)).label("escalated_count"),
            )
            .where(
                Conversation.org_id == org_id,
                func.date(Conversation.created_at) >= start,
                func.date(Conversation.created_at) <= end,
            )
            .group_by(Conversation.chatbot_id)
            .order_by(func.count(Conversation.id).desc())
        )
        rows = result.all()
        return [
            {
                "chatbot_id":           str(row.chatbot_id),
                "total_conversations":  row.total_conversations or 0,
                "total_messages":       int(row.total_messages or 0),
                "resolved_count":       int(row.resolved_count or 0),
                "escalated_count":      int(row.escalated_count or 0),
            }
            for row in rows
        ]

    # ── Daily time-series ──────────────────────────────────────────────────────

    async def get_daily_series(
        self, org_id: UUID, chatbot_id: UUID, start: date, end: date,
    ) -> List[ChatbotAnalyticsDaily]:
        result = await self.db.execute(
            select(ChatbotAnalyticsDaily).where(
                ChatbotAnalyticsDaily.org_id == org_id,
                ChatbotAnalyticsDaily.chatbot_id == chatbot_id,
                ChatbotAnalyticsDaily.date >= start,
                ChatbotAnalyticsDaily.date <= end,
            ).order_by(ChatbotAnalyticsDaily.date)
        )
        return list(result.scalars().all())

    # ── AI Decision Log ────────────────────────────────────────────────────────

    async def list_decision_logs(
        self, org_id: UUID,
        chatbot_id: Optional[UUID] = None,
        was_escalated: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        from app.modules.chat.models import AiDecisionLog
        q = select(AiDecisionLog).where(AiDecisionLog.org_id == org_id)
        if chatbot_id:
            q = q.where(AiDecisionLog.chatbot_id == chatbot_id)
        if was_escalated is not None:
            q = q.where(AiDecisionLog.was_escalated == was_escalated)
        q = q.order_by(AiDecisionLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Token usage report ─────────────────────────────────────────────────────

    async def get_usage_records(
        self, org_id: UUID, year: int, month: int
    ) -> List[UsageRecord]:
        result = await self.db.execute(
            select(UsageRecord).where(
                UsageRecord.org_id == org_id,
                UsageRecord.period_year == year,
                UsageRecord.period_month == month,
            ).order_by(UsageRecord.tokens_used.desc())
        )
        return list(result.scalars().all())

    async def get_ledger_by_action(
        self, org_id: UUID, start: date, end: date,
    ) -> Dict[str, int]:
        """Sum of tokens debited per action type."""
        result = await self.db.execute(
            select(
                TokenLedger.action,
                func.sum(TokenLedger.tokens).label("total"),
            )
            .where(
                TokenLedger.org_id == org_id,
                TokenLedger.type == TokenLedgerType.debit,
                func.date(TokenLedger.created_at) >= start,
                func.date(TokenLedger.created_at) <= end,
            )
            .group_by(TokenLedger.action)
        )
        return {row.action: int(row.total) for row in result.all()}
