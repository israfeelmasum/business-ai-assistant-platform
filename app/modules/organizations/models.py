"""
Organizations module — SQLAlchemy ORM models.
Tables: organizations, org_members, api_keys
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    Enum as SAEnum, ForeignKey, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MemberRole(str, enum.Enum):
    admin   = "admin"
    editor  = "editor"
    viewer  = "viewer"
    agent   = "agent"


class ApiKeyScope(str, enum.Enum):
    chat        = "chat"
    admin       = "admin"
    knowledge   = "knowledge"
    analytics   = "analytics"
    full        = "full"


class Organization(Base):
    __tablename__ = "organizations"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                    = Column(String(255), nullable=False)
    slug                    = Column(String(100), nullable=False, unique=True, index=True)
    logo_url                = Column(Text)
    favicon_url             = Column(Text)
    website                 = Column(String(255))
    email                   = Column(String(255))
    phone                   = Column(String(30))
    address                 = Column(Text)
    country                 = Column(String(100))
    timezone                = Column(String(100), nullable=False, default="UTC")
    default_language        = Column(String(10), nullable=False, default="en")
    custom_domain           = Column(String(255))
    # Branding
    brand_color_primary     = Column(String(7), default="#2563EB")
    brand_color_secondary   = Column(String(7), default="#7C3AED")
    brand_color_accent      = Column(String(7), default="#06B6D4")
    # Legal
    privacy_policy_url      = Column(Text)
    terms_url               = Column(Text)
    # Business hours JSON: {"mon": {"open": "09:00", "close": "18:00"}, ...}
    business_hours          = Column(JSONB, default=dict)
    settings                = Column(JSONB, default=dict)
    is_active               = Column(Boolean, nullable=False, default=True)
    created_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at              = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    members         = relationship("OrgMember", back_populates="organization", cascade="all, delete-orphan")
    api_keys        = relationship("ApiKey", back_populates="organization", cascade="all, delete-orphan")
    subscription    = relationship("Subscription", back_populates="organization", uselist=False)


class OrgMember(Base):
    __tablename__ = "org_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_members"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role        = Column(SAEnum(MemberRole, name="member_role"), nullable=False, default=MemberRole.viewer)
    invited_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at   = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    organization    = relationship("Organization", back_populates="members")
    user            = relationship("User", foreign_keys=[user_id], back_populates="org_memberships")
    inviter         = relationship("User", foreign_keys=[invited_by])


class ApiKey(Base):
    __tablename__ = "api_keys"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id  = Column(UUID(as_uuid=True), nullable=True, index=True)  # FK to chatbots added when chatbot module loads
    name        = Column(String(100), nullable=False)
    key_prefix  = Column(String(10), nullable=False)
    key_hash    = Column(String(255), nullable=False, unique=True)
    scopes      = Column(ARRAY(SAEnum(ApiKeyScope, name="api_key_scope", create_type=False)), nullable=False, default=list)
    last_used_at = Column(DateTime(timezone=True))
    expires_at  = Column(DateTime(timezone=True))
    is_active   = Column(Boolean, nullable=False, default=True)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="api_keys")
