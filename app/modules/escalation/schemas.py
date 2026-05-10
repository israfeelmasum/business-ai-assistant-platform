"""
Escalation module — Pydantic schemas.
Extends the basic EscalationResponse from chat/schemas.py with
agent-console-specific views and write schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.chat.models import EscalationTrigger, EscalationStatus
from app.modules.chat.schemas import (
    ConversationResponse, MessageResponse, EscalationResponse
)


# ── Escalation Detail (agent console view) ────────────────────────────────────

class EscalationDetailResponse(BaseModel):
    """Full escalation detail including conversation + messages."""
    model_config = ConfigDict(from_attributes=True)

    escalation:     EscalationResponse
    conversation:   ConversationResponse
    messages:       List[MessageResponse]
    is_overdue:     bool = False


# ── Assign / Resolve ───────────────────────────────────────────────────────────

class AssignEscalationRequest(BaseModel):
    agent_id: UUID


class ResolveEscalationRequest(BaseModel):
    notes: Optional[str] = None


# ── Agent sends a message in an escalated conversation ────────────────────────

class AgentMessageRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


# ── Canned Responses ───────────────────────────────────────────────────────────

class CannedResponseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    org_id:         UUID
    chatbot_id:     Optional[UUID]
    title:          str
    content:        str
    tags:           Optional[List[str]]
    created_by:     Optional[UUID]
    created_at:     datetime
    updated_at:     datetime


class CreateCannedResponseRequest(BaseModel):
    title:      str
    content:    str
    chatbot_id: Optional[UUID] = None   # None = applies to all chatbots in org
    tags:       Optional[List[str]] = None

    @field_validator("title", "content")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class UpdateCannedResponseRequest(BaseModel):
    title:      Optional[str] = None
    content:    Optional[str] = None
    tags:       Optional[List[str]] = None
    chatbot_id: Optional[UUID] = None
