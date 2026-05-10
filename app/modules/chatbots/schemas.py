"""
Chatbots module — Pydantic schemas.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.chatbots.models import (
    PersonalityType, DomainType, FallbackBehavior,
    PromptLayer, DeploymentChannel, ProviderSource
)


# ── Chatbot Core ───────────────────────────────────────────────────────────────

class ChatbotCreateRequest(BaseModel):
    name:           str
    slug:           Optional[str] = None
    description:    Optional[str] = None
    avatar_url:     Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class ChatbotUpdateRequest(BaseModel):
    name:           Optional[str] = None
    description:    Optional[str] = None
    avatar_url:     Optional[str] = None
    is_active:      Optional[bool] = None
    is_published:   Optional[bool] = None


class ChatbotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    org_id:         UUID
    name:           str
    slug:           str
    description:    Optional[str]
    avatar_url:     Optional[str]
    is_active:      bool
    is_published:   bool
    created_by:     Optional[UUID]
    created_at:     datetime
    updated_at:     datetime


class ChatbotDetailResponse(ChatbotResponse):
    """Full response including nested config objects."""
    persona:        Optional["PersonaResponse"] = None
    theme:          Optional["ThemeResponse"] = None
    prechat_form:   Optional["PrechatFormResponse"] = None
    active_prompts: List["PromptResponse"] = []
    deployments:    List["DeploymentResponse"] = []


# ── Model Config ───────────────────────────────────────────────────────────────

class ModelConfigSetRequest(BaseModel):
    task:               str  # model_capability value
    provider_source:    ProviderSource = ProviderSource.platform
    provider_id:        Optional[UUID] = None
    org_provider_id:    Optional[UUID] = None
    model_id:           str
    parameters:         Optional[Dict[str, Any]] = None


class ModelConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    chatbot_id:         UUID
    task:               str
    provider_source:    ProviderSource
    provider_id:        Optional[UUID]
    org_provider_id:    Optional[UUID]
    model_id:           str
    parameters:         Dict[str, Any]
    is_active:          bool


# ── Persona ────────────────────────────────────────────────────────────────────

class PersonaCreateRequest(BaseModel):
    persona_name:           str = "Assistant"
    personality:            PersonalityType = PersonalityType.professional
    domain:                 DomainType = DomainType.general
    default_language:       str = "en"
    supported_languages:    List[str] = ["en"]
    greeting_message:       Optional[str] = None
    farewell_message:       Optional[str] = None
    offline_message:        Optional[str] = None
    fallback_behavior:      FallbackBehavior = FallbackBehavior.escalate
    voice_id:               Optional[str] = None
    voice_speed:            Decimal = Decimal("1.0")


class PersonaUpdateRequest(BaseModel):
    persona_name:           Optional[str] = None
    personality:            Optional[PersonalityType] = None
    domain:                 Optional[DomainType] = None
    default_language:       Optional[str] = None
    supported_languages:    Optional[List[str]] = None
    greeting_message:       Optional[str] = None
    farewell_message:       Optional[str] = None
    offline_message:        Optional[str] = None
    fallback_behavior:      Optional[FallbackBehavior] = None
    voice_id:               Optional[str] = None
    voice_speed:            Optional[Decimal] = None


class PersonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     UUID
    chatbot_id:             UUID
    persona_name:           str
    personality:            PersonalityType
    domain:                 DomainType
    default_language:       str
    supported_languages:    List[str]
    greeting_message:       Optional[str]
    farewell_message:       Optional[str]
    offline_message:        Optional[str]
    fallback_behavior:      FallbackBehavior
    voice_id:               Optional[str]
    voice_speed:            Optional[Decimal]
    is_active:              bool
    version:                int
    updated_at:             datetime


# ── Prompts ────────────────────────────────────────────────────────────────────

class PromptCreateRequest(BaseModel):
    layer:      PromptLayer
    name:       str
    content:    str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt content cannot be empty")
        return v


class PromptUpdateRequest(BaseModel):
    name:       Optional[str] = None
    content:    Optional[str] = None
    is_active:  Optional[bool] = None


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    chatbot_id: UUID
    layer:      PromptLayer
    name:       str
    content:    str
    is_active:  bool
    version:    int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ── Guardrails ─────────────────────────────────────────────────────────────────

class GuardrailCreateRequest(BaseModel):
    name:           str
    rule_type:      str
    rule_config:    Dict[str, Any] = {}


class GuardrailUpdateRequest(BaseModel):
    name:           Optional[str] = None
    rule_config:    Optional[Dict[str, Any]] = None
    is_active:      Optional[bool] = None


class GuardrailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    chatbot_id:     UUID
    name:           str
    rule_type:      str
    rule_config:    Dict[str, Any]
    is_active:      bool
    created_at:     datetime


# ── Deployments ────────────────────────────────────────────────────────────────

class DeploymentCreateRequest(BaseModel):
    channel:    DeploymentChannel
    name:       Optional[str] = None
    config:     Dict[str, Any] = {}
    api_key_id: Optional[UUID] = None


class DeploymentUpdateRequest(BaseModel):
    name:       Optional[str] = None
    config:     Optional[Dict[str, Any]] = None
    api_key_id: Optional[UUID] = None
    is_active:  Optional[bool] = None


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    chatbot_id: UUID
    channel:    DeploymentChannel
    name:       Optional[str]
    config:     Dict[str, Any]
    api_key_id: Optional[UUID]
    is_active:  bool
    created_at: datetime
    updated_at: datetime


# ── Theme ──────────────────────────────────────────────────────────────────────

class ThemeUpdateRequest(BaseModel):
    color_primary:          Optional[str] = None
    color_secondary:        Optional[str] = None
    color_accent:           Optional[str] = None
    color_background:       Optional[str] = None
    color_text:             Optional[str] = None
    color_user_bubble:      Optional[str] = None
    color_bot_bubble:       Optional[str] = None
    font_family:            Optional[str] = None
    font_size_base:         Optional[int] = None
    border_radius:          Optional[int] = None
    widget_width:           Optional[int] = None
    widget_height:          Optional[int] = None
    position:               Optional[str] = None
    dark_mode_enabled:      Optional[bool] = None
    dark_color_background:  Optional[str] = None
    dark_color_text:        Optional[str] = None
    custom_css:             Optional[str] = None
    rtl_enabled:            Optional[bool] = None
    template_name:          Optional[str] = None
    # Widget branding & fallback contacts
    logo_url:               Optional[str] = None
    welcome_message:        Optional[str] = None
    fallback_whatsapp:      Optional[str] = None
    fallback_email:         Optional[str] = None
    fallback_phone:         Optional[str] = None
    fallback_message:       Optional[str] = None


class ThemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     UUID
    chatbot_id:             UUID
    color_primary:          Optional[str]
    color_secondary:        Optional[str]
    color_accent:           Optional[str]
    color_background:       Optional[str]
    color_text:             Optional[str]
    color_user_bubble:      Optional[str]
    color_bot_bubble:       Optional[str]
    font_family:            Optional[str]
    font_size_base:         Optional[int]
    border_radius:          Optional[int]
    widget_width:           Optional[int]
    widget_height:          Optional[int]
    position:               Optional[str]
    dark_mode_enabled:      bool
    dark_color_background:  Optional[str]
    dark_color_text:        Optional[str]
    custom_css:             Optional[str]
    rtl_enabled:            bool
    template_name:          Optional[str]
    # Widget branding & fallback contacts
    logo_url:               Optional[str] = None
    welcome_message:        Optional[str] = None
    fallback_whatsapp:      Optional[str] = None
    fallback_email:         Optional[str] = None
    fallback_phone:         Optional[str] = None
    fallback_message:       Optional[str] = None
    updated_at:             datetime


class WidgetConfigResponse(BaseModel):
    """Public (no-auth) widget configuration — returned on widget init."""
    model_config = ConfigDict(from_attributes=True)

    chatbot_id:         UUID
    chatbot_name:       str
    # Colors
    color_primary:      str = "#2563EB"
    color_user_bubble:  str = "#2563EB"
    color_bot_bubble:   str = "#F3F4F6"
    color_background:   str = "#FFFFFF"
    color_text:         str = "#111827"
    # Branding
    logo_url:           Optional[str] = None
    welcome_message:    str = "Hello! How can I help you today?"
    persona_name:       str = "Assistant"
    greeting_message:   Optional[str] = None
    # Fallback contacts
    fallback_whatsapp:  Optional[str] = None
    fallback_email:     Optional[str] = None
    fallback_phone:     Optional[str] = None
    fallback_message:   str = "Our team is here to help. Reach us via:"
    # Layout
    position:           str = "bottom-right"
    widget_width:       int = 380
    widget_height:      int = 600
    border_radius:      int = 12
    font_family:        str = "Inter"


# ── Prechat Form ───────────────────────────────────────────────────────────────

class PrechatFormUpdateRequest(BaseModel):
    is_enabled:     Optional[bool] = None
    title:          Optional[str] = None
    message:        Optional[str] = None
    fields:         Optional[List[Dict[str, Any]]] = None
    remember_user:  Optional[bool] = None


class PrechatFormResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    chatbot_id:     UUID
    is_enabled:     bool
    title:          Optional[str]
    message:        Optional[str]
    fields:         List[Dict[str, Any]]
    remember_user:  bool
    updated_at:     datetime


# Allow forward references
ChatbotDetailResponse.model_rebuild()
