"""
Organizations repository — DB operations for organizations, members, api_keys.
"""

import re
import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.organizations.models import Organization, OrgMember, ApiKey

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:80]


class OrganizationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, slug: str, owner_id: UUID, **kwargs) -> Organization:
        org = Organization(name=name, slug=slug, **kwargs)
        self.db.add(org)
        await self.db.flush()
        # Auto-add creator as admin member
        member = OrgMember(org_id=org.id, user_id=owner_id, role="admin")
        self.db.add(member)
        await self.db.flush()
        return org

    async def get_by_id(self, org_id: UUID) -> Optional[Organization]:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        result = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(select(Organization.id).where(Organization.slug == slug))
        return result.scalar_one_or_none() is not None

    async def unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        count = 1
        while await self.slug_exists(slug):
            slug = f"{base_slug}-{count}"
            count += 1
        return slug

    async def get_user_orgs(self, user_id: UUID) -> List[Organization]:
        result = await self.db.execute(
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(OrgMember.user_id == user_id, Organization.is_active == True)
            .order_by(Organization.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, org_id: UUID, **kwargs) -> Optional[Organization]:
        from datetime import datetime, timezone
        await self.db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(**kwargs, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_by_id(org_id)

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[Organization]:
        """Super-admin: list all organizations."""
        result = await self.db.execute(
            select(Organization)
            .order_by(Organization.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count(Organization.id)))
        return result.scalar_one()

    async def count_active(self) -> int:
        result = await self.db.execute(
            select(func.count(Organization.id)).where(Organization.is_active == True)
        )
        return result.scalar_one()

    async def count_members(self, org_id: UUID) -> int:
        """Count members for a given org."""
        result = await self.db.execute(
            select(func.count(OrgMember.id)).where(OrgMember.org_id == org_id)
        )
        return result.scalar_one()


class MemberRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_membership(self, org_id: UUID, user_id: UUID) -> Optional[OrgMember]:
        result = await self.db.execute(
            select(OrgMember).where(
                OrgMember.org_id == org_id,
                OrgMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_org_members(self, org_id: UUID) -> List[OrgMember]:
        result = await self.db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id)
            .order_by(OrgMember.joined_at)
        )
        return list(result.scalars().all())

    async def add_member(self, org_id: UUID, user_id: UUID,
                         role: str, invited_by: UUID = None) -> OrgMember:
        member = OrgMember(
            org_id=org_id, user_id=user_id,
            role=role, invited_by=invited_by
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def update_role(self, org_id: UUID, user_id: UUID, role: str) -> None:
        await self.db.execute(
            update(OrgMember)
            .where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
            .values(role=role)
        )

    async def remove_member(self, org_id: UUID, user_id: UUID) -> None:
        await self.db.execute(
            delete(OrgMember).where(
                OrgMember.org_id == org_id,
                OrgMember.user_id == user_id,
            )
        )

    async def count_admins(self, org_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(OrgMember.id)).where(
                OrgMember.org_id == org_id,
                OrgMember.role == "admin",
            )
        )
        return result.scalar_one()


class ApiKeyRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, org_id: UUID, name: str, key_prefix: str,
                     key_hash: str, scopes: list, created_by: UUID,
                     chatbot_id: UUID = None, expires_at=None) -> ApiKey:
        key = ApiKey(
            org_id=org_id, name=name,
            key_prefix=key_prefix, key_hash=key_hash,
            scopes=scopes, chatbot_id=chatbot_id,
            expires_at=expires_at, created_by=created_by,
        )
        self.db.add(key)
        await self.db.flush()
        return key

    async def get_by_id(self, key_id: UUID, org_id: UUID) -> Optional[ApiKey]:
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        from datetime import datetime, timezone
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()
        if key and key.expires_at and key.expires_at < datetime.now(timezone.utc):
            return None
        return key

    async def list_org_keys(self, org_id: UUID) -> List[ApiKey]:
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.org_id == org_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, key_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.org_id == org_id)
            .values(is_active=False)
        )

    async def touch_last_used(self, key_id: UUID) -> None:
        from datetime import datetime, timezone
        await self.db.execute(
            update(ApiKey).where(ApiKey.id == key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
