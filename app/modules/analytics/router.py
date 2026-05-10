"""
Analytics module — router.

All endpoints require JWT (org member).

GET /organizations/{org_id}/analytics/dashboard          — overview stats
GET /organizations/{org_id}/analytics/chatbots           — per-chatbot breakdown
GET /organizations/{org_id}/analytics/daily/{chatbot_id} — daily time series
GET /organizations/{org_id}/analytics/audit-logs         — AI decision log
GET /organizations/{org_id}/analytics/token-usage        — token report
"""

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.analytics.schemas import (
    DashboardStats, ChatbotStats, DailyAnalyticsRow,
    AiDecisionLogResponse, TokenUsageReport, AnalyticsReportResponse,
)
from app.modules.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analytics & Audit Trail"])


@router.get(
    "/organizations/{org_id}/analytics/dashboard",
    response_model=DashboardStats,
)
async def get_dashboard(
    org_id: UUID,
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD), default: 30 days ago"),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD), default: today"),
    chatbot_id: Optional[UUID] = Query(None, description="Filter to a single chatbot"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Organization dashboard: conversation volumes, quality scores,
    unique users, token usage, escalation queue depth.
    Defaults to last 30 days across all chatbots.
    """
    svc = AnalyticsService(db)
    return await svc.get_dashboard(
        org_id, requester_id=current_user.id,
        start=start, end=end, chatbot_id=chatbot_id,
    )


@router.get(
    "/organizations/{org_id}/analytics/chatbots",
    response_model=List[ChatbotStats],
)
async def get_chatbot_breakdown(
    org_id: UUID,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Per-chatbot breakdown: conversations, messages, resolution/escalation counts.
    Sorted by conversation volume (highest first).
    """
    svc = AnalyticsService(db)
    return await svc.get_chatbot_stats(org_id, requester_id=current_user.id,
                                       start=start, end=end)


@router.get(
    "/organizations/{org_id}/analytics/daily/{chatbot_id}",
    response_model=List[DailyAnalyticsRow],
)
async def get_daily_series(
    org_id: UUID,
    chatbot_id: UUID,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Daily time-series for a specific chatbot.
    Used to render charts in the admin dashboard.
    Returns pre-aggregated rows from chatbot_analytics_daily.
    Empty dates within the range are omitted (no zero-fill).
    """
    svc = AnalyticsService(db)
    return await svc.get_daily_series(
        org_id, chatbot_id, requester_id=current_user.id,
        start=start, end=end,
    )


@router.get(
    "/organizations/{org_id}/analytics/audit-logs",
    response_model=List[AiDecisionLogResponse],
)
async def get_audit_logs(
    org_id: UUID,
    chatbot_id: Optional[UUID] = Query(None),
    was_escalated: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI Decision Audit Log — every inference decision recorded by the chat engine.

    Includes: system prompt snapshot, retrieved context, model used, confidence,
    EIL score, latency breakdown, escalation flag.

    Filter by chatbot or escalated-only for targeted compliance review.
    """
    svc = AnalyticsService(db)
    return await svc.list_decision_logs(
        org_id, requester_id=current_user.id,
        chatbot_id=chatbot_id,
        was_escalated=was_escalated,
        limit=limit, offset=offset,
    )


@router.get(
    "/organizations/{org_id}/analytics/token-usage",
    response_model=TokenUsageReport,
)
async def get_token_usage_report(
    org_id: UUID,
    year: int = Query(..., ge=2024, le=2099),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Monthly token usage report.
    Breaks down consumption by chatbot and by action type
    (chat_message, embedding, vision, tts, stt, translation).
    Includes a rough USD cost estimate.
    """
    svc = AnalyticsService(db)
    return await svc.get_token_usage_report(
        org_id, requester_id=current_user.id,
        year=year, month=month,
    )


@router.post(
    "/organizations/{org_id}/analytics/reports/generate",
    response_model=AnalyticsReportResponse,
)
async def generate_analytics_report(
    org_id: UUID,
    period_type: str = Query(..., description="weekly | monthly | yearly"),
    period_label: str = Query(..., description="e.g. 2026-W15 | 2026-04 | 2026"),
    chatbot_id: Optional[UUID] = Query(None, description="Scope to a single chatbot"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate (or regenerate) a period analytics report with an AI-written executive
    summary powered by Ollama.  Results are upserted to analytics_reports so they can
    be retrieved cheaply later.

    **period_type / period_label examples**
    - `weekly`  / `2026-W15`
    - `monthly` / `2026-04`
    - `yearly`  / `2026`
    """
    svc = AnalyticsService(db)
    return await svc.generate_report(
        org_id, requester_id=current_user.id,
        period_type=period_type, period_label=period_label,
        chatbot_id=chatbot_id,
    )


@router.get(
    "/organizations/{org_id}/analytics/reports",
    response_model=List[AnalyticsReportResponse],
)
async def list_analytics_reports(
    org_id: UUID,
    period_type: Optional[str] = Query(None, description="weekly | monthly | yearly"),
    chatbot_id: Optional[UUID] = Query(None),
    limit: int = Query(12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve previously generated analytics reports for this organisation,
    newest first.  Use the generate endpoint to create a new one or refresh an
    existing one.
    """
    svc = AnalyticsService(db)
    return await svc.list_reports(
        org_id, requester_id=current_user.id,
        period_type=period_type,
        chatbot_id=chatbot_id,
        limit=limit,
    )
