"""
Chat module — Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.chat.models import (
    ConversationStatus, MessageRole, MessageType,
    EscalationTrigger, EscalationStatus
)


# ── End User ───────────────────────────────────────────────────────────────────

class EndUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id:                     UUID
    org_id:                 UUID
    chatbot_id:             UUID
    external_id:            Optional[str]
    name:                   Optional[str]
    email:                  Optional[str]
    phone:                  Optional[str]
    language:               Optional[str]
    timezone:               Optional[str]
    metadata:               Dict[str, Any] = Field(default_factory=dict, alias='extra_data', serialization_alias='metadata')
    profile_summary:        Optional[str]
    total_conversations:    int
    last_seen_at:           Optional[datetime]
    created_at:             datetime


# ── Chat Session ───────────────────────────────────────────────────────────────

class StartChatRequest(BaseModel):
    """Called by the widget to start or resume a conversation."""
    chatbot_id:     UUID
    session_id:     str             # Client-generated session identifier
    external_id:    Optional[str] = None    # Device fingerprint
    channel:        str = "web_widget"
    prechat_data:   Optional[Dict[str, Any]] = None
    user_info:      Optional[Dict[str, Any]] = None
    # Tracking
    utm_source:     Optional[str] = None
    utm_medium:     Optional[str] = None
    referrer_url:   Optional[str] = None
    user_agent:     Optional[str] = None
    language:       Optional[str] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    chatbot_id:         UUID
    org_id:             UUID
    session_id:         str
    channel:            str
    status:             ConversationStatus
    language_detected:  Optional[str]
    message_count:      int
    user_message_count: int
    created_at:         datetime
    updated_at:         datetime


# ── Chat Message ───────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    """User sends a message to the chatbot."""
    content:        str
    type:           MessageType = MessageType.text
    attachments:    Optional[List[Dict[str, Any]]] = None
    image_base64:   Optional[str] = None  # Base64-encoded image for vision analysis

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    conversation_id: UUID
    org_id:         UUID
    role:           MessageRole
    type:           MessageType
    content:        Optional[str]
    attachments:    List[Any]
    model_used:     Optional[str]
    tokens_input:   Optional[int]
    tokens_output:  Optional[int]
    latency_ms:     Optional[int]
    confidence:     Optional[Decimal]
    eil_score:      Optional[Decimal]
    intent:         Optional[str]
    rag_sources:    List[Any]
    suggestions:    Optional[List[str]]
    action_data:    Optional[Dict[str, Any]]
    trace_id:       Optional[UUID]
    created_at:     datetime


# ── Escalation ─────────────────────────────────────────────────────────────────

class EscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    conversation_id:    UUID
    trigger:            EscalationTrigger
    status:             EscalationStatus
    assigned_agent_id:  Optional[UUID]
    assigned_at:        Optional[datetime]
    sla_minutes:        int
    sla_deadline:       Optional[datetime]
    resolved_at:        Optional[datetime]
    created_at:         datetime


# ── Reaction ───────────────────────────────────────────────────────────────────

class ReactMessageRequest(BaseModel):
    reaction:   str     # thumbs_up | thumbs_down | flag
    comment:    Optional[str] = None

    @field_validator("reaction")
    @classmethod
    def valid_reaction(cls, v: str) -> str:
        if v not in ("thumbs_up", "thumbs_down", "flag"):
            raise ValueError("reaction must be thumbs_up, thumbs_down, or flag")
        return v


# ── Conversation History ───────────────────────────────────────────────────────

class ConversationHistoryResponse(BaseModel):
    conversation:   ConversationResponse
    messages:       List[MessageResponse]
    escalation:     Optional[EscalationResponse] = None
