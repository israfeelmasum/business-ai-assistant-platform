"""
Auth service — business logic for register, login, refresh, password reset.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository, SessionRepository, PasswordResetRepository
from app.modules.auth.schemas import (
    RegisterRequest, LoginRequest, LoginResponse,
    TokenPair, UserResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    CompanySignupRequest, CreateAdminRequest,
)
from app.modules.auth.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    hash_refresh_token, hash_api_key
)
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.users    = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.resets   = PasswordResetRepository(db)

    # ── Register ───────────────────────────────────────────────────────────────

    async def register(self, req: RegisterRequest, ip: str = None) -> LoginResponse:
        if await self.users.email_exists(req.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )

        user = await self.users.create(
            email=req.email,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            phone=req.phone,
        )
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"New user registered: {user.email} (id={user.id})")
        return await self._issue_tokens(user, ip=ip)

    # ── Login ──────────────────────────────────────────────────────────────────

    async def login(self, req: LoginRequest, ip: str = None,
                    user_agent: str = None) -> LoginResponse:
        user = await self.users.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support."
            )

        await self.users.update_last_login(user.id)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User logged in: {user.email} from {ip}")
        return await self._issue_tokens(user, ip=ip, user_agent=user_agent)

    # ── Refresh Token ──────────────────────────────────────────────────────────

    async def refresh(self, req: RefreshRequest, ip: str = None) -> TokenPair:
        token_hash = hash_refresh_token(req.refresh_token)
        session = await self.sessions.get_by_token_hash(token_hash)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        user = await self.users.get_by_id(session.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated"
            )

        # Rotate refresh token (invalidate old, issue new)
        await self.sessions.revoke(token_hash)

        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self.sessions.create(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            ip_address=ip,
        )

        access_token, expires_in = create_access_token(user.id, user.role.value, user.email)
        await self.db.commit()

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
        )

    # ── Logout ─────────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        await self.sessions.revoke(token_hash)
        await self.db.commit()

    async def logout_all(self, user_id: UUID) -> None:
        await self.sessions.revoke_all_for_user(user_id)
        await self.db.commit()

    # ── Forgot Password ────────────────────────────────────────────────────────

    async def forgot_password(self, req: ForgotPasswordRequest) -> str:
        """Returns reset token (send via email in router). Silently succeeds if email not found."""
        user = await self.users.get_by_email(req.email)
        if not user:
            # Don't reveal whether email exists
            return ""

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        await self.resets.create(user.id, token_hash)
        await self.db.commit()

        logger.info(f"Password reset requested for: {user.email}")
        return raw_token  # Caller sends this via email

    # ── Reset Password ─────────────────────────────────────────────────────────

    async def reset_password(self, req: ResetPasswordRequest) -> None:
        token_hash = hashlib.sha256(req.token.encode()).hexdigest()
        reset = await self.resets.get_valid(token_hash)
        if not reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        await self.users.update_profile(
            reset.user_id,
            password_hash=hash_password(req.new_password)
        )
        await self.resets.mark_used(reset.id)
        # Revoke all active sessions for security
        await self.sessions.revoke_all_for_user(reset.user_id)
        await self.db.commit()

    # ── Change Password ────────────────────────────────────────────────────────

    async def change_password(self, user_id: UUID, req: ChangePasswordRequest) -> None:
        user = await self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(req.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        await self.users.update_profile(
            user_id,
            password_hash=hash_password(req.new_password)
        )
        await self.sessions.revoke_all_for_user(user_id)
        await self.db.commit()

    # ── Company Signup ─────────────────────────────────────────────────────────

    async def company_signup(self, req: CompanySignupRequest,
                             ip: str = None) -> LoginResponse:
        """Create user + org + membership in one transaction."""
        from app.modules.organizations.repository import OrganizationRepository
        from app.modules.organizations.models import OrgMember

        if await self.users.email_exists(req.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )

        # 1. Create user
        user = await self.users.create(
            email=req.email,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            phone=req.phone,
        )

        # 2. Create organization
        org_repo = OrganizationRepository(self.db)
        import re

        def _slugify(name: str) -> str:
            slug = re.sub(r"[^\w\s-]", "", name.lower())
            slug = re.sub(r"[\s_]+", "-", slug).strip("-")
            return slug[:80]

        base_slug = _slugify(req.company_slug or req.company_name)
        slug = await org_repo.unique_slug(base_slug)
        org = await org_repo.create(
            name=req.company_name,
            slug=slug,
            owner_id=user.id,
        )

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            f"Company signup: user={user.email} org={org.name} (id={org.id})"
        )
        response = await self._issue_tokens(user, ip=ip)
        # Populate default_org_id with the newly created org
        response.user.default_org_id = org.id
        return response

    # ── Create Super Admin ─────────────────────────────────────────────────────

    async def create_super_admin(self, req: CreateAdminRequest,
                                 ip: str = None) -> LoginResponse:
        """Create a super_admin user. Allowed if no super_admin exists yet, or by existing super_admin."""
        from sqlalchemy import select
        from app.modules.auth.models import UserRole

        # Check if any super_admin already exists
        result = await self.db.execute(
            select(User).where(User.role == UserRole.super_admin).limit(1)
        )
        existing_admin = result.scalar_one_or_none()
        # Note: the router enforces auth when an admin already exists;
        # here we just do the creation regardless (caller is responsible for the guard).

        if await self.users.email_exists(req.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )

        user = await self.users.create(
            email=req.email,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            phone=req.phone,
            role=UserRole.super_admin.value,
        )
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"Super admin created: {user.email} (id={user.id})")
        return await self._issue_tokens(user, ip=ip)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _issue_tokens(self, user: User, ip: str = None,
                            user_agent: str = None) -> LoginResponse:
        access_token, expires_in = create_access_token(user.id, user.role.value, user.email)
        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        await self.sessions.create(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=user_agent,
        )

        user_resp = UserResponse.model_validate(user)

        # Populate default_org_id from the user's first org membership
        if not user_resp.default_org_id:
            try:
                from app.modules.organizations.repository import OrganizationRepository
                org_repo = OrganizationRepository(self.db)
                orgs = await org_repo.get_user_orgs(user.id)
                if orgs:
                    user_resp.default_org_id = orgs[0].id
            except Exception:
                pass  # Non-critical — dashboard will gracefully handle missing org

        return LoginResponse(
            user=user_resp,
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=raw_refresh,
                expires_in=expires_in,
            )
        )
