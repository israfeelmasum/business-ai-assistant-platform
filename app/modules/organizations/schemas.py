"""
Organizations module — Pydantic schemas.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.modules.organizations.models import MemberRole


# ─── Super Admin ──────────────────────────────────────────────────────────────

class OrgAdminResponse(BaseModel):
    """Extended org response for super_admin listing — includes member count."""
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str]
    website: Optional[str]
    email: Optional[str]
    country: Optional[str]
    timezone: str
    is_active: bool
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformStatsResponse(BaseModel):
    total_orgs: int
    active_orgs: int
    total_users: int


class OrgListResponse(BaseModel):
    items: List[OrgAdminResponse]
    total: int
    limit: int
    offset: int


# ─── Organization ─────────────────────────────────────────────────────────────

class OrgCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None          # auto-generated from name if not provided
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    default_language: str = "en"
    brand_color_primary: str = "#2563EB"
    brand_color_secondary: str = "#7C3AED"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Organization name cannot be empty")
        return v.strip()


class OrgUpdateRequest(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    default_language: Optional[str] = None
    custom_domain: Optional[str] = None
    brand_color_primary: Optional[str] = None
    brand_color_secondary: Optional[str] = None
    brand_color_accent: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_url: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str]
    favicon_url: Optional[str]
    website: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    country: Optional[str]
    timezone: str
    default_language: str
    custom_domain: Optional[str]
    brand_color_primary: str
    brand_color_secondary: str
    brand_color_accent: str
    privacy_policy_url: Optional[str]
    terms_url: Optional[str]
    business_hours: Optional[Dict]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgSummary(BaseModel):
    """Lightweight org summary for lists."""
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str]
    timezone: str
    default_language: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Members ──────────────────────────────────────────────────────────────────

class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: MemberRole = MemberRole.viewer


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    org_id: UUID
    role: MemberRole
    joined_at: datetime
    # Flattened user info
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = ["chat"]
    chatbot_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: List[str]
    chatbot_id: Optional[UUID]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    # Only shown once on creation
    raw_key: Optional[str] = None

    model_config = {"from_attributes": True}
