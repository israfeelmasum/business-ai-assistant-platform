"""
Organizations service — business logic for org management, members, api keys.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models import Organization, OrgMember, ApiKey
from app.modules.organizations.repository import (
    OrganizationRepository, MemberRepository, ApiKeyRepository
)
from app.modules.organizations.schemas import (
    OrgCreateRequest, OrgUpdateRequest, OrgResponse,
    InviteMemberRequest, UpdateMemberRoleRequest,
    ApiKeyCreateRequest, ApiKeyResponse, MemberResponse
)
from app.modules.auth.repository import UserRepository
from app.modules.auth.security import generate_api_key

logger = logging.getLogger(__name__)


class OrganizationService:

    def __init__(self, db: AsyncSession):
        self.db      = db
        self.orgs    = OrganizationRepository(db)
        self.members = MemberRepository(db)
        self.keys    = ApiKeyRepository(db)
        self.users   = UserRepository(db)

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_org(self, req: OrgCreateRequest, owner_id: UUID) -> OrgResponse:
        from app.modules.organizations.repository import _slugify
        base_slug = req.slug or _slugify(req.name)
        slug = await self.orgs.unique_slug(base_slug)

        org = await self.orgs.create(
            name=req.name,
            slug=slug,
            owner_id=owner_id,
            email=req.email,
            phone=req.phone,
            website=req.website,
            country=req.country,
            timezone=req.timezone,
            default_language=req.default_language,
            brand_color_primary=req.brand_color_primary,
            brand_color_secondary=req.brand_color_secondary,
        )
        await self.db.commit()
        await self.db.refresh(org)
        logger.info(f"Organization created: {org.name} (id={org.id}) by user={owner_id}")
        return OrgResponse.model_validate(org)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_org(self, org_id: UUID, requester_id: UUID) -> OrgResponse:
        org = await self._get_org_or_404(org_id)
        await self._require_membership(org_id, requester_id)
        return OrgResponse.model_validate(org)

    async def get_user_orgs(self, user_id: UUID) -> List[OrgResponse]:
        orgs = await self.orgs.get_user_orgs(user_id)
        return [OrgResponse.model_validate(o) for o in orgs]

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update_org(self, org_id: UUID, req: OrgUpdateRequest,
                         requester_id: UUID) -> OrgResponse:
        await self._require_admin(org_id, requester_id)
        updates = req.model_dump(exclude_unset=True)
        if not updates:
            org = await self._get_org_or_404(org_id)
            return OrgResponse.model_validate(org)

        org = await self.orgs.update(org_id, **updates)
        await self.db.commit()
        await self.db.refresh(org)
        return OrgResponse.model_validate(org)

    # ── Members ────────────────────────────────────────────────────────────────

    async def get_members(self, org_id: UUID, requester_id: UUID) -> List[MemberResponse]:
        await self._require_membership(org_id, requester_id)
        members = await self.members.get_org_members(org_id)
        result = []
        for m in members:
            user = await self.users.get_by_id(m.user_id)
            resp = MemberResponse.model_validate(m)
            if user:
                resp.user_email  = user.email
                resp.user_name   = user.full_name
                resp.user_avatar = user.avatar_url
            result.append(resp)
        return result

    async def invite_member(self, org_id: UUID, req: InviteMemberRequest,
                            inviter_id: UUID) -> MemberResponse:
        await self._require_admin(org_id, inviter_id)

        # Find user by email
        user = await self.users.get_by_email(req.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No account found for {req.email}. Ask them to register first."
            )

        # Check if already a member
        existing = await self.members.get_membership(org_id, user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization"
            )

        member = await self.members.add_member(
            org_id=org_id,
            user_id=user.id,
            role=req.role.value,
            invited_by=inviter_id,
        )
        await self.db.commit()
        await self.db.refresh(member)

        resp = MemberResponse.model_validate(member)
        resp.user_email  = user.email
        resp.user_name   = user.full_name
        resp.user_avatar = user.avatar_url
        return resp

    async def update_member_role(self, org_id: UUID, user_id: UUID,
                                  req: UpdateMemberRoleRequest,
                                  requester_id: UUID) -> None:
        await self._require_admin(org_id, requester_id)

        # Cannot demote yourself if you're the last admin
        if user_id == requester_id and req.role.value != "admin":
            admin_count = await self.members.count_admins(org_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last admin. Promote another member first."
                )

        await self.members.update_role(org_id, user_id, req.role.value)
        await self.db.commit()

    async def remove_member(self, org_id: UUID, user_id: UUID,
                             requester_id: UUID) -> None:
        await self._require_admin(org_id, requester_id)

        # Cannot remove last admin
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        if member.role == "admin":
            admin_count = await self.members.count_admins(org_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last admin of an organization"
                )

        await self.members.remove_member(org_id, user_id)
        await self.db.commit()

    # ── API Keys ───────────────────────────────────────────────────────────────

    async def create_api_key(self, org_id: UUID, req: ApiKeyCreateRequest,
                              creator_id: UUID) -> ApiKeyResponse:
        await self._require_admin(org_id, creator_id)

        raw_key, key_prefix, key_hash = generate_api_key(prefix="fb")
        key = await self.keys.create(
            org_id=org_id,
            name=req.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=req.scopes,
            created_by=creator_id,
            chatbot_id=req.chatbot_id,
            expires_at=req.expires_at,
        )
        await self.db.commit()
        await self.db.refresh(key)

        resp = ApiKeyResponse.model_validate(key)
        resp.raw_key = raw_key  # shown ONCE
        logger.info(f"API key created: {key.name} for org={org_id}")
        return resp

    async def list_api_keys(self, org_id: UUID, requester_id: UUID) -> List[ApiKeyResponse]:
        await self._require_membership(org_id, requester_id)
        keys = await self.keys.list_org_keys(org_id)
        return [ApiKeyResponse.model_validate(k) for k in keys]

    async def revoke_api_key(self, org_id: UUID, key_id: UUID,
                              requester_id: UUID) -> None:
        await self._require_admin(org_id, requester_id)
        await self.keys.revoke(key_id, org_id)
        await self.db.commit()

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_org_or_404(self, org_id: UUID) -> Organization:
        org = await self.orgs.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Organization not found")
        return org

    async def _require_membership(self, org_id: UUID, user_id: UUID) -> OrgMember:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
        return member

    async def _require_admin(self, org_id: UUID, user_id: UUID) -> OrgMember:
        member = await self._require_membership(org_id, user_id)
        if member.role not in ("admin",):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admin role required")
        return member
