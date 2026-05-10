"""
Analytics module — Pydantic schemas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Daily Analytics Row ────────────────────────────────────────────────────────

class DailyAnalyticsRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date:                   date
    total_conversations:    int
    new_conversations:      int
    total_messages:         int
    avg_confidence:         Optional[Decimal]
    avg_eil_score:          Optional[Decimal]
    avg_response_ms:        Optional[int]
    resolved_count:         int
    escalated_count:        int
    abandoned_count:        int
    unique_users:           int
    returning_users:        int
    tokens_used:            int


# ── Dashboard Stats ────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Summary stats for the org dashboard — computed live from DB."""
    org_id:                         UUID
    period_start:                   date
    period_end:                     date
    # Conversations
    total_conversations:            int
    active_conversations:           int
    resolved_conversations:         int
    escalated_conversations:        int
    # Messages
    total_messages:                 int
    avg_messages_per_conversation:  float
    # Performance
    avg_response_ms:                Optional[int]
    avg_confidence:                 Optional[float]
    avg_eil_score:                  Optional[float]
    # Users
    total_unique_users:             int
    # Tokens
    total_tokens_used:              int
    estimated_cost_usd:             float
    # Escalations
    pending_escalations:            int
    overdue_escalations:            int


class ChatbotStats(BaseModel):
    """Per-chatbot breakdown within a period."""
    chatbot_id:             UUID
    chatbot_name:           str
    total_conversations:    int
    total_messages:         int
    resolved_count:         int
    escalated_count:        int
    tokens_used:            int
    avg_confidence:         Optional[float]


# ── AI Decision Log ────────────────────────────────────────────────────────────

class AiDecisionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     UUID
    trace_id:               UUID
    message_id:             Optional[UUID]
    conversation_id:        Optional[UUID]
    chatbot_id:             Optional[UUID]
    org_id:                 UUID
    user_message:           Optional[str]
    ai_response:            Optional[str]
    model_used:             Optional[str]
    provider_type:          Optional[str]
    tokens_input:           Optional[int]
    tokens_output:          Optional[int]
    confidence:             Optional[Decimal]
    eil_score:              Optional[Decimal]
    intent:                 Optional[str]
    vector_search_ms:       Optional[int]
    llm_ttft_ms:            Optional[int]
    total_latency_ms:       Optional[int]
    was_escalated:          bool
    was_hallucination_risk: bool
    created_at:             datetime


# ── Token Usage Report ─────────────────────────────────────────────────────────

class TokenUsageReport(BaseModel):
    org_id:         UUID
    period_year:    int
    period_month:   int
    total_tokens:   int
    by_chatbot:     List[Dict[str, Any]]
    by_action:      Dict[str, int]
    estimated_cost_usd: float


# ── Analytics Report (AI-summarised period report) ─────────────────────────────

class AnalyticsReportResponse(BaseModel):
    id:                     UUID
    org_id:                 UUID
    chatbot_id:             Optional[UUID]
    period_type:            str          # weekly | monthly | yearly
    period_label:           str          # e.g. "2026-W15" | "2026-04" | "2026"
    period_start:           date
    period_end:             date
    total_conversations:    int
    total_messages:         int
    escalation_count:       int
    escalation_rate:        float
    avg_confidence:         float
    unique_users:           int
    top_questions:          List[Dict[str, Any]]
    staff_stats:            List[Dict[str, Any]]
    ai_summary:             Optional[str]
    generated_at:           datetime
