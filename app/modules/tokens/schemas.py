"""
Tokens module — Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.tokens.models import TokenLedgerType, TokenAction


# ── Token Packages ─────────────────────────────────────────────────────────────

class TokenPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    name:           str
    tokens:         int
    price:          Decimal
    currency:       str
    bonus_tokens:   int
    is_active:      bool
    created_at:     datetime


class CreateTokenPackageRequest(BaseModel):
    """Super-admin only: create a top-up package."""
    name:           str
    tokens:         int
    price:          Decimal
    currency:       str = "USD"
    bonus_tokens:   int = 0

    @field_validator("tokens", "bonus_tokens")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


# ── Token Ledger ───────────────────────────────────────────────────────────────

class TokenLedgerEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id:             UUID
    org_id:         UUID
    chatbot_id:     Optional[UUID]
    type:           TokenLedgerType
    action:         TokenAction
    tokens:         int
    balance_after:  int
    reference_id:   Optional[UUID]
    model_used:     Optional[str]
    metadata:       Optional[Dict[str, Any]] = Field(None, alias='extra_data', serialization_alias='metadata')
    created_at:     datetime


class OrgTokenBalance(BaseModel):
    """Current token balance derived from the ledger."""
    org_id:         UUID
    balance:        int
    last_updated:   Optional[datetime]


# ── Usage Records ──────────────────────────────────────────────────────────────

class UsageRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                         UUID
    org_id:                     UUID
    chatbot_id:                 Optional[UUID]
    period_year:                int
    period_month:               int
    messages_count:             int
    tokens_used:                int
    storage_bytes_used:         int
    api_calls_count:            int
    vision_calls_count:         int
    tts_calls_count:            int
    stt_calls_count:            int
    translation_calls_count:    int
    unique_users_count:         int
    escalations_count:          int
    updated_at:                 datetime


# ── Internal ───────────────────────────────────────────────────────────────────

class DebitTokensRequest(BaseModel):
    """Used internally by the Chat Engine to debit tokens for an AI action."""
    action:         TokenAction
    tokens:         int
    chatbot_id:     Optional[UUID] = None
    reference_id:   Optional[UUID] = None
    model_used:     Optional[str] = None
    metadata:       Optional[Dict[str, Any]] = None
