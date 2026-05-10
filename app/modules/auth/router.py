"""
Auth router — public + protected auth endpoints.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.schemas import (
    RegisterRequest, LoginRequest, LoginResponse, TokenPair,
    RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, UserResponse, UserUpdateRequest,
    CompanySignupRequest, CreateAdminRequest,
)
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Register ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account. Returns JWT tokens immediately."""
    svc = AuthService(db)
    return await svc.register(req, ip=_get_client_ip(request))


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password. Returns JWT access + refresh tokens."""
    svc = AuthService(db)
    return await svc.login(
        req,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


# ── Refresh ────────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    req: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token — returns a new access + refresh token pair."""
    svc = AuthService(db)
    return await svc.refresh(req, ip=_get_client_ip(request))


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke the current refresh token (logout from this device)."""
    svc = AuthService(db)
    await svc.logout(req.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke ALL refresh tokens for this user (logout from all devices)."""
    svc = AuthService(db)
    await svc.logout_all(current_user.id)


# ── Forgot / Reset Password ──���─────────────────────────────────────────────────

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email. Always returns 200 (no email enumeration)."""
    svc = AuthService(db)
    raw_token = await svc.forgot_password(req)
    if raw_token:
        # TODO: background_tasks.add_task(send_reset_email, req.email, raw_token)
        logger.info(f"[DEV] Password reset token for {req.email}: {raw_token}")
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token from email."""
    svc = AuthService(db)
    await svc.reset_password(req)
    return {"message": "Password reset successfully. Please login."}


# ── Profile (protected) ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user's profile, including their default org."""
    from sqlalchemy import select
    from app.modules.organizations.models import OrgMember
    result = await db.execute(
        select(OrgMember.org_id)
        .where(OrgMember.user_id == current_user.id)
        .order_by(OrgMember.joined_at)
        .limit(1)
    )
    org_row = result.scalar_one_or_none()
    resp = UserResponse.model_validate(current_user)
    resp.default_org_id = org_row
    return resp


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile."""
    from app.modules.auth.repository import UserRepository
    repo = UserRepository(db)
    updates = req.model_dump(exclude_unset=True)
    if not updates:
        return UserResponse.model_validate(current_user)
    user = await repo.update_profile(current_user.id, **updates)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change password (requires current password)."""
    svc = AuthService(db)
    await svc.change_password(current_user.id, req)
    return {"message": "Password changed successfully."}


# ── Company Signup ─────────────────────────────────────────────────────────────

@router.post("/company-signup", response_model=LoginResponse,
             status_code=status.HTTP_201_CREATED)
async def company_signup(
    req: CompanySignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new company account.

    Creates a user, an organization, and links the user as org admin in one
    atomic transaction. Returns JWT tokens and user profile with default_org_id.
    """
    svc = AuthService(db)
    return await svc.company_signup(req, ip=_get_client_ip(request))


# ── Create Super Admin ─────────────────────────────────────────────────────────

@router.post("/create-admin", response_model=LoginResponse,
             status_code=status.HTTP_201_CREATED)
async def create_admin(
    req: CreateAdminRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    """Create a super_admin user.

    This endpoint is open (no auth required) ONLY when no super_admin exists yet.
    Once at least one super_admin exists, an existing super_admin JWT is required.
    """
    from sqlalchemy import select
    from app.modules.auth.models import UserRole as _Role
    from app.modules.auth.repository import UserRepository
    from app.modules.auth.security import verify_access_token
    from uuid import UUID as _UUID

    # Check if any super_admin already exists
    result = await db.execute(
        select(User).where(User.role == _Role.super_admin).limit(1)
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin is not None:
        # Require the caller to be an authenticated super_admin
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required: a super_admin already exists",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = verify_access_token(credentials.credentials)
        caller_id = _UUID(payload["sub"])
        repo = UserRepository(db)
        caller = await repo.get_by_id(caller_id)
        if not caller or caller.role != _Role.super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an existing super_admin can create another super_admin",
            )

    svc = AuthService(db)
    return await svc.create_super_admin(req, ip=_get_client_ip(request))
