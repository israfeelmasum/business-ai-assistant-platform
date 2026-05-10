"""
Organizations router — org management, members, API keys.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.organizations.models import OrgMember
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import (
    OrgCreateRequest, OrgUpdateRequest, OrgResponse,
    InviteMemberRequest, UpdateMemberRoleRequest, MemberResponse,
    ApiKeyCreateRequest, ApiKeyResponse,
    OrgAdminResponse, OrgListResponse, PlatformStatsResponse,
)
from app.modules.organizations.service import OrganizationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ── Super Admin: platform-wide routes ─────────────────────────────────────────

@router.get("/stats", response_model=PlatformStatsResponse,
            summary="Platform stats (super_admin only)")
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Return total orgs, active orgs, and total users across the platform."""
    from app.modules.auth.models import User as UserModel
    from app.modules.organizations.models import Organization

    repo = OrganizationRepository(db)
    total_orgs = await repo.count_all()
    active_orgs = await repo.count_active()

    user_count_result = await db.execute(select(func.count(UserModel.id)))
    total_users = user_count_result.scalar_one()

    return PlatformStatsResponse(
        total_orgs=total_orgs,
        active_orgs=active_orgs,
        total_users=total_users,
    )


@router.get("/all", response_model=OrgListResponse,
            summary="List ALL organizations (super_admin only)")
async def list_all_organizations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """Paginated list of all organizations with member count. Requires super_admin."""
    repo = OrganizationRepository(db)
    orgs = await repo.list_all(limit=limit, offset=offset)
    total = await repo.count_all()

    items = []
    for org in orgs:
        member_count = await repo.count_members(org.id)
        items.append(OrgAdminResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            website=org.website,
            email=org.email,
            country=org.country,
            timezone=org.timezone,
            is_active=org.is_active,
            member_count=member_count,
            created_at=org.created_at,
        ))

    return OrgListResponse(items=items, total=total, limit=limit, offset=offset)


# ── Organizations ──────────────────────────────────────────────────────────────

@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrgCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization. Caller becomes the admin."""
    svc = OrganizationService(db)
    return await svc.create_org(req, owner_id=current_user.id)


@router.get("", response_model=List[OrgResponse])
async def list_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all organizations the current user belongs to."""
    svc = OrganizationService(db)
    return await svc.get_user_orgs(current_user.id)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get organization details (must be a member)."""
    svc = OrganizationService(db)
    return await svc.get_org(org_id, requester_id=current_user.id)


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_organization(
    org_id: UUID,
    req: OrgUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update organization profile (admin only)."""
    svc = OrganizationService(db)
    return await svc.update_org(org_id, req, requester_id=current_user.id)


# ── Members ────────────────────────────────────────────────────────────────────

@router.get("/{org_id}/members", response_model=List[MemberResponse])
async def list_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all members of an organization."""
    svc = OrganizationService(db)
    return await svc.get_members(org_id, requester_id=current_user.id)


@router.post("/{org_id}/members", response_model=MemberResponse,
             status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: UUID,
    req: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a registered user to the organization (admin only)."""
    svc = OrganizationService(db)
    return await svc.invite_member(org_id, req, inviter_id=current_user.id)


@router.patch("/{org_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    req: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a member's role (admin only)."""
    svc = OrganizationService(db)
    await svc.update_member_role(org_id, user_id, req, requester_id=current_user.id)
    return {"message": "Role updated"}


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from the organization (admin only)."""
    svc = OrganizationService(db)
    await svc.remove_member(org_id, user_id, requester_id=current_user.id)


# ── API Keys ───────────────────────────────────────────────────────────────────

@router.get("/{org_id}/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the organization."""
    svc = OrganizationService(db)
    return await svc.list_api_keys(org_id, requester_id=current_user.id)


@router.post("/{org_id}/api-keys", response_model=ApiKeyResponse,
             status_code=status.HTTP_201_CREATED)
async def create_api_key(
    org_id: UUID,
    req: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new API key. Raw key shown ONCE — store it safely."""
    svc = OrganizationService(db)
    return await svc.create_api_key(org_id, req, creator_id=current_user.id)


@router.delete("/{org_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    org_id: UUID,
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key (admin only)."""
    svc = OrganizationService(db)
    await svc.revoke_api_key(org_id, key_id, requester_id=current_user.id)
