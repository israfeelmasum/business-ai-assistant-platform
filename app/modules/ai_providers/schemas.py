"""
AI Providers module — Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.ai_providers.models import ProviderType, ModelCapability


# ── Platform Provider ──────────────────────────────────────────────────────────

class AiProviderCreateRequest(BaseModel):
    name:           str
    provider_type:  ProviderType
    base_url:       Optional[str] = None
    api_key:        Optional[str] = None    # Plain key — encrypted before storage
    config:         Optional[Dict[str, Any]] = None
    is_default:     bool = False


class AiProviderUpdateRequest(BaseModel):
    name:           Optional[str] = None
    base_url:       Optional[str] = None
    api_key:        Optional[str] = None    # Plain key — encrypted before storage
    config:         Optional[Dict[str, Any]] = None
    is_active:      Optional[bool] = None
    is_default:     Optional[bool] = None


class AiProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    name:           str
    provider_type:  ProviderType
    base_url:       Optional[str]
    # api_key_enc NEVER returned — just indicate if key is set
    has_api_key:    bool = False
    config:         Dict[str, Any]
    is_active:      bool
    is_default:     bool
    created_at:     datetime
    updated_at:     datetime

    @classmethod
    def from_orm_with_key_flag(cls, obj) -> "AiProviderResponse":
        data = {
            "id": obj.id,
            "name": obj.name,
            "provider_type": obj.provider_type,
            "base_url": obj.base_url,
            "has_api_key": bool(obj.api_key_enc),
            "config": obj.config or {},
            "is_active": obj.is_active,
            "is_default": obj.is_default,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        return cls(**data)


# ── Provider Model ─────────────────────────────────────────────────────────────

class AiProviderModelCreateRequest(BaseModel):
    model_id:               str
    display_name:           str
    capability:             ModelCapability
    context_window:         Optional[int] = None
    max_tokens:             Optional[int] = None
    cost_input_per_1m:      Decimal = Decimal("0")
    cost_output_per_1m:     Decimal = Decimal("0")
    sort_order:             int = 0


class AiProviderModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 UUID
    provider_id:        UUID
    model_id:           str
    display_name:       str
    capability:         ModelCapability
    context_window:     Optional[int]
    max_tokens:         Optional[int]
    cost_input_per_1m:  Decimal
    cost_output_per_1m: Decimal
    is_active:          bool
    sort_order:         int


# ── BYOK (Org AI Provider) ─────────────────────────────────────────────────────

class OrgAiProviderCreateRequest(BaseModel):
    name:           str
    provider_type:  ProviderType
    base_url:       Optional[str] = None
    api_key:        str             # Required — BYOK key
    config:         Optional[Dict[str, Any]] = None

    @field_validator("api_key")
    @classmethod
    def key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("api_key cannot be empty")
        return v.strip()


class OrgAiProviderUpdateRequest(BaseModel):
    name:       Optional[str] = None
    base_url:   Optional[str] = None
    api_key:    Optional[str] = None
    config:     Optional[Dict[str, Any]] = None
    is_active:  Optional[bool] = None


class OrgAiProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    org_id:         UUID
    name:           str
    provider_type:  ProviderType
    base_url:       Optional[str]
    has_api_key:    bool = True     # Always True — required on create
    config:         Dict[str, Any]
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime

    @classmethod
    def from_orm_safe(cls, obj) -> "OrgAiProviderResponse":
        return cls(
            id=obj.id,
            org_id=obj.org_id,
            name=obj.name,
            provider_type=obj.provider_type,
            base_url=obj.base_url,
            has_api_key=bool(obj.api_key_enc),
            config=obj.config or {},
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
