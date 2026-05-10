"""
Analytics module — business logic.
"""

import json
import logging
import uuid as _uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import (
    DashboardStats, ChatbotStats, DailyAnalyticsRow,
    AiDecisionLogResponse, TokenUsageReport, AnalyticsReportResponse,
)
import httpx
import os
from app.modules.chatbots.repository import ChatbotRepository
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)


class AnalyticsService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.repo       = AnalyticsRepository(db)
        self.chatbots   = ChatbotRepository(db)
        self.members    = MemberRepository(db)

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Not a member of this organization")

    # ── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(
        self,
        org_id: UUID,
        requester_id: UUID,
        start: Optional[date] = None,
        end: Optional[date] = None,
        chatbot_id: Optional[UUID] = None,
    ) -> DashboardStats:
        await self._require_member(org_id, requester_id)

        today = date.today()
        if end is None:
            end = today
        if start is None:
            start = today - timedelta(days=29)   # default: last 30 days

        conv_stats  = await self.repo.get_conversation_stats(org_id, start, end, chatbot_id)
        msg_stats   = await self.repo.get_message_stats(org_id, start, end, chatbot_id)
        unique_users = await self.repo.get_unique_users(org_id, start, end, chatbot_id)
        esc_counts  = await self.repo.get_escalation_counts(org_id)
        token_stats = await self.repo.get_token_totals(org_id, start, end)

        total = conv_stats["total_conversations"]
        total_msgs = msg_stats["total_messages"]

        return DashboardStats(
            org_id=org_id,
            period_start=start,
            period_end=end,
            total_conversations=total,
            active_conversations=conv_stats["active_conversations"],
            resolved_conversations=conv_stats["resolved_conversations"],
            escalated_conversations=conv_stats["escalated_conversations"],
            total_messages=total_msgs,
            avg_messages_per_conversation=conv_stats["avg_messages_per_conversation"],
            avg_response_ms=msg_stats["avg_response_ms"],
            avg_confidence=msg_stats["avg_confidence"],
            avg_eil_score=msg_stats["avg_eil_score"],
            total_unique_users=unique_users,
            total_tokens_used=token_stats["total_tokens_used"],
            estimated_cost_usd=token_stats["estimated_cost_usd"],
            pending_escalations=esc_counts["pending_escalations"],
            overdue_escalations=esc_counts["overdue_escalations"],
        )

    # ── Chatbot breakdown ──────────────────────────────────────────────────────

    async def get_chatbot_stats(
        self, org_id: UUID, requester_id: UUID,
        start: Optional[date] = None, end: Optional[date] = None,
    ) -> List[ChatbotStats]:
        await self._require_member(org_id, requester_id)

        today = date.today()
        end = end or today
        start = start or (today - timedelta(days=29))

        rows = await self.repo.get_chatbot_breakdown(org_id, start, end)
        result = []
        for row in rows:
            chatbot = await self.chatbots.get_by_id(UUID(row["chatbot_id"]))
            result.append(ChatbotStats(
                chatbot_id=UUID(row["chatbot_id"]),
                chatbot_name=chatbot.name if chatbot else "(deleted)",
                total_conversations=row["total_conversations"],
                total_messages=row["total_messages"],
                resolved_count=row["resolved_count"],
                escalated_count=row["escalated_count"],
                tokens_used=0,  # could join token ledger if needed
                avg_confidence=None,
            ))
        return result

    # ── Daily time series ──────────────────────────────────────────────────────

    async def get_daily_series(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID,
        start: Optional[date] = None, end: Optional[date] = None,
    ) -> List[DailyAnalyticsRow]:
        await self._require_member(org_id, requester_id)

        today = date.today()
        end = end or today
        start = start or (today - timedelta(days=29))

        rows = await self.repo.get_daily_series(org_id, chatbot_id, start, end)
        return [DailyAnalyticsRow.model_validate(r) for r in rows]

    # ── AI Decision Logs ───────────────────────────────────────────────────────

    async def list_decision_logs(
        self, org_id: UUID, requester_id: UUID,
        chatbot_id: Optional[UUID] = None,
        was_escalated: Optional[bool] = None,
        limit: int = 100, offset: int = 0,
    ) -> List[AiDecisionLogResponse]:
        await self._require_member(org_id, requester_id)
        logs = await self.repo.list_decision_logs(
            org_id, chatbot_id=chatbot_id,
            was_escalated=was_escalated,
            limit=limit, offset=offset,
        )
        return [AiDecisionLogResponse.model_validate(l) for l in logs]

    # ── Token Usage Report ─────────────────────────────────────────────────────

    async def get_token_usage_report(
        self, org_id: UUID, requester_id: UUID,
        year: int, month: int,
    ) -> TokenUsageReport:
        await self._require_member(org_id, requester_id)

        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)

        records = await self.repo.get_usage_records(org_id, year, month)
        by_action = await self.repo.get_ledger_by_action(org_id, start, end)

        total = sum(r.tokens_used for r in records) or sum(by_action.values())
        cost = total * 0.000002

        by_chatbot = [
            {
                "chatbot_id": str(r.chatbot_id) if r.chatbot_id else None,
                "tokens_used": r.tokens_used,
                "message_count": r.messages_count,
            }
            for r in records
        ]

        return TokenUsageReport(
            org_id=org_id,
            period_year=year,
            period_month=month,
            total_tokens=total,
            by_chatbot=by_chatbot,
            by_action=by_action,
            estimated_cost_usd=cost,
        )

    # ── AI-summarised Period Reports ───────────────────────────────────────────

    async def generate_report(
        self,
        org_id: UUID,
        requester_id: UUID,
        period_type: str,
        period_label: str,
        chatbot_id: Optional[UUID] = None,
    ) -> AnalyticsReportResponse:
        """
        Generate (or regenerate) a period analytics report with an AI summary.
        period_type : weekly | monthly | yearly
        period_label: "2026-W15" | "2026-04" | "2026"
        """
        await self._require_member(org_id, requester_id)

        # ── Resolve date range from label ──────────────────────────────────────
        today = date.today()
        if period_type == "weekly":
            # label "YYYY-Www"
            try:
                parts = period_label.split("-W")
                yr, wk = int(parts[0]), int(parts[1])
                # ISO week Monday
                import datetime as _dt
                period_start = _dt.date.fromisocalendar(yr, wk, 1)
                period_end   = _dt.date.fromisocalendar(yr, wk, 7)
            except Exception:
                period_end   = today
                period_start = today - timedelta(days=6)
        elif period_type == "monthly":
            try:
                from calendar import monthrange as _mr
                yr, mo = int(period_label[:4]), int(period_label[5:7])
                _, last = _mr(yr, mo)
                period_start = date(yr, mo, 1)
                period_end   = date(yr, mo, last)
            except Exception:
                period_end   = today.replace(day=1) - timedelta(days=1)
                period_start = period_end.replace(day=1)
        elif period_type == "yearly":
            try:
                yr = int(period_label)
                period_start = date(yr, 1, 1)
                period_end   = date(yr, 12, 31)
            except Exception:
                period_start = date(today.year, 1, 1)
                period_end   = today
        else:
            period_end   = today
            period_start = today - timedelta(days=29)

        # ── Gather core stats ──────────────────────────────────────────────────
        dash = await self.get_dashboard(org_id, requester_id,
                                        start=period_start, end=period_end,
                                        chatbot_id=chatbot_id)

        total_convs  = dash.total_conversations
        total_msgs   = dash.total_messages
        esc_count    = dash.escalated_conversations
        esc_rate     = round(esc_count / total_convs, 4) if total_convs else 0.0
        avg_conf     = float(dash.avg_confidence or 0.0)
        unique_users = dash.total_unique_users

        # ── Top questions from decision log ───────────────────────────────────
        top_q_sql = text("""
            SELECT user_message, COUNT(*) AS cnt
            FROM ai_decision_logs
            WHERE org_id = :org_id
              AND created_at::date BETWEEN :start AND :end
              AND user_message IS NOT NULL
              AND (:chatbot_id IS NULL OR chatbot_id = :chatbot_id)
            GROUP BY user_message
            ORDER BY cnt DESC
            LIMIT 10
        """)
        try:
            import uuid as _uuid_tq
            tq_result = await self.db.execute(top_q_sql, {
                "org_id": _uuid_tq.UUID(str(org_id)),
                "start": period_start,
                "end": period_end,
                "chatbot_id": _uuid_tq.UUID(str(chatbot_id)) if chatbot_id else None,
            })
            top_questions = [
                {"question": row[0], "count": row[1]}
                for row in tq_result.fetchall()
            ]
        except Exception as exc:
            logger.warning("top_questions query failed: %s", exc)
            top_questions = []
            try:
                await self.db.rollback()
            except Exception:
                pass

        # ── Staff response stats (messages sent by human agents) ──────────────
        staff_sql = text("""
            SELECT m.agent_id, u.email, u.full_name,
                   COUNT(*) AS messages_sent
            FROM messages m
            JOIN users u ON u.id = m.agent_id
            WHERE m.role = 'agent'
              AND m.created_at::date BETWEEN :start AND :end
              AND (:org_id IS NULL OR m.org_id = :org_id)
              AND m.agent_id IS NOT NULL
            GROUP BY m.agent_id, u.email, u.full_name
            ORDER BY messages_sent DESC
            LIMIT 20
        """)
        try:
            import uuid as _uuid_st
            staff_result = await self.db.execute(staff_sql, {
                "start": period_start,
                "end": period_end,
                "org_id": _uuid_st.UUID(str(org_id)),
            })
            staff_stats = [
                {
                    "user_id": str(row[0]),
                    "email": row[1],
                    "name": row[2],
                    "messages_sent": row[3],
                }
                for row in staff_result.fetchall()
            ]
        except Exception as exc:
            logger.warning("staff_stats query failed: %s", exc)
            staff_stats = []
            try:
                await self.db.rollback()
            except Exception:
                pass

        # ── AI summary via Ollama ──────────────────────────────────────────────
        ai_summary: Optional[str] = None
        try:
            summary_prompt = (
                f"You are a business analytics assistant. "
                f"Write a concise 3-5 sentence executive summary for a {period_type} "
                f"chatbot analytics report ({period_label}).\n\n"
                f"Key metrics:\n"
                f"- Total conversations: {total_convs}\n"
                f"- Total messages: {total_msgs}\n"
                f"- Escalations: {esc_count} ({esc_rate*100:.1f}%)\n"
                f"- Average confidence: {avg_conf*100:.1f}%\n"
                f"- Unique users: {unique_users}\n"
                f"Top questions: {json.dumps([q['question'] for q in top_questions[:5]])}\n\n"
                f"Focus on trends, performance highlights, and actionable insights."
            )
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_key = os.getenv("OLLAMA_API_KEY", "")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{ollama_url.rstrip('/')}/api/chat",
                    json={
                        "model": "llama3.2:latest",
                        "messages": [{"role": "user", "content": summary_prompt}],
                        "stream": False,
                        "temperature": 0.4,
                    },
                    headers={"X-API-Key": ollama_key},
                )
                resp.raise_for_status()
                data = resp.json()
                if "message" in data:
                    ai_summary = data["message"].get("content", "")
                elif "choices" in data:
                    ai_summary = data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("AI summary generation failed: %s", exc)

        # ── Upsert to analytics_reports table ─────────────────────────────────
        report_id = _uuid.uuid4()
        now_utc   = datetime.now(timezone.utc)
        upsert_sql = text("""
            INSERT INTO analytics_reports (
                id, org_id, chatbot_id, period_type, period_label,
                period_start, period_end,
                total_conversations, total_messages, escalation_count,
                escalation_rate, avg_confidence, unique_users,
                top_questions, staff_stats, ai_summary, generated_at
            ) VALUES (
                :id, :org_id, :chatbot_id, :period_type, :period_label,
                :period_start, :period_end,
                :total_conversations, :total_messages, :escalation_count,
                :escalation_rate, :avg_confidence, :unique_users,
                CAST(:top_questions AS jsonb), CAST(:staff_stats AS jsonb),
                :ai_summary, :generated_at
            )
            ON CONFLICT (org_id, period_type, period_label, chatbot_id)
            DO UPDATE SET
                total_conversations = EXCLUDED.total_conversations,
                total_messages      = EXCLUDED.total_messages,
                escalation_count    = EXCLUDED.escalation_count,
                escalation_rate     = EXCLUDED.escalation_rate,
                avg_confidence      = EXCLUDED.avg_confidence,
                unique_users        = EXCLUDED.unique_users,
                top_questions       = EXCLUDED.top_questions,
                staff_stats         = EXCLUDED.staff_stats,
                ai_summary          = EXCLUDED.ai_summary,
                generated_at        = EXCLUDED.generated_at
            RETURNING id
        """)
        try:
            import uuid as _uuid_mod
            result = await self.db.execute(upsert_sql, {
                "id": _uuid_mod.UUID(str(report_id)),
                "org_id": _uuid_mod.UUID(str(org_id)),
                "chatbot_id": _uuid_mod.UUID(str(chatbot_id)) if chatbot_id else None,
                "period_type": period_type,
                "period_label": period_label,
                "period_start": period_start,
                "period_end": period_end,
                "total_conversations": total_convs,
                "total_messages": total_msgs,
                "escalation_count": esc_count,
                "escalation_rate": float(esc_rate),
                "avg_confidence": float(avg_conf),
                "unique_users": unique_users,
                "top_questions": json.dumps(top_questions),
                "staff_stats": json.dumps(staff_stats),
                "ai_summary": ai_summary,
                "generated_at": now_utc,
            })
            row = result.fetchone()
            if row:
                report_id = row[0]
            await self.db.commit()
        except Exception as exc:
            logger.warning("analytics_reports upsert failed: %s", exc)
            try:
                await self.db.rollback()
            except Exception:
                pass

        return AnalyticsReportResponse(
            id=report_id,
            org_id=org_id,
            chatbot_id=chatbot_id,
            period_type=period_type,
            period_label=period_label,
            period_start=period_start,
            period_end=period_end,
            total_conversations=total_convs,
            total_messages=total_msgs,
            escalation_count=esc_count,
            escalation_rate=esc_rate,
            avg_confidence=avg_conf,
            unique_users=unique_users,
            top_questions=top_questions,
            staff_stats=staff_stats,
            ai_summary=ai_summary,
            generated_at=now_utc,
        )

    async def list_reports(
        self,
        org_id: UUID,
        requester_id: UUID,
        period_type: Optional[str] = None,
        chatbot_id: Optional[UUID] = None,
        limit: int = 12,
    ) -> List[AnalyticsReportResponse]:
        """Return previously generated analytics reports for this org."""
        await self._require_member(org_id, requester_id)

        try:
            from sqlalchemy import select as _select
            from app.modules.analytics.models import AnalyticsReport as _AR
            q = _select(_AR).where(_AR.org_id == org_id)
            if period_type:
                q = q.where(_AR.period_type == period_type)
            if chatbot_id:
                q = q.where(_AR.chatbot_id == chatbot_id)
            q = q.order_by(_AR.generated_at.desc()).limit(limit)
            result = await self.db.execute(q)
            orm_rows = result.scalars().all()
            rows = [
                {
                    "id": r.id,
                    "org_id": r.org_id,
                    "chatbot_id": r.chatbot_id,
                    "period_type": r.period_type,
                    "period_label": r.period_label,
                    "period_start": r.period_start,
                    "period_end": r.period_end,
                    "total_conversations": r.total_conversations,
                    "total_messages": r.total_messages,
                    "escalation_count": r.escalation_count,
                    "escalation_rate": r.escalation_rate,
                    "avg_confidence": r.avg_confidence,
                    "unique_users": r.unique_users,
                    "top_questions": r.top_questions,
                    "staff_stats": r.staff_stats,
                    "ai_summary": r.ai_summary,
                    "generated_at": r.generated_at,
                }
                for r in orm_rows
            ]
        except Exception as exc:
            logger.warning("list_reports query failed: %s", exc)
            return []

        reports = []
        for r in rows:
            tq = r["top_questions"]
            ss = r["staff_stats"]
            if isinstance(tq, str):
                tq = json.loads(tq)
            if isinstance(ss, str):
                ss = json.loads(ss)
            reports.append(AnalyticsReportResponse(
                id=r["id"],
                org_id=r["org_id"],
                chatbot_id=r["chatbot_id"],
                period_type=r["period_type"],
                period_label=r["period_label"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                total_conversations=r["total_conversations"],
                total_messages=r["total_messages"],
                escalation_count=r["escalation_count"],
                escalation_rate=float(r["escalation_rate"] or 0),
                avg_confidence=float(r["avg_confidence"] or 0),
                unique_users=r["unique_users"],
                top_questions=tq or [],
                staff_stats=ss or [],
                ai_summary=r["ai_summary"],
                generated_at=r["generated_at"],
            ))
        return reports
