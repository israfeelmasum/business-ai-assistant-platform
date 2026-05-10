"""
Auth module — SQLAlchemy ORM models.
Tables: users, user_sessions, password_reset_tokens
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    org_admin   = "org_admin"
    member      = "member"
    agent       = "agent"


class User(Base):
    __tablename__ = "users"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email          = Column(String(255), nullable=False, unique=True, index=True)
    password_hash  = Column(String(255), nullable=False)
    full_name      = Column(String(255), nullable=False)
    avatar_url     = Column(Text)
    phone          = Column(String(30))
    role           = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.member)
    is_active      = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    last_login_at  = Column(DateTime(timezone=True))
    created_at     = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    sessions       = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    reset_tokens   = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    org_memberships = relationship("OrgMember", back_populates="user",
                                   foreign_keys="OrgMember.user_id",
                                   cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=False, unique=True)
    device_info        = Column(JSONB, default=dict)
    ip_address         = Column(INET)
    user_agent         = Column(Text)
    expires_at         = Column(DateTime(timezone=True), nullable=False)
    revoked_at         = Column(DateTime(timezone=True))
    created_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash  = Column(String(255), nullable=False, unique=True)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    used_at     = Column(DateTime(timezone=True))
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="reset_tokens")
