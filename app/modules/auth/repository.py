"""
Auth repository — database operations for users and sessions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, UserSession, PasswordResetToken
from app.modules.auth.security import hash_refresh_token

logger = logging.getLogger(__name__)


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, full_name: str,
                     phone: Optional[str] = None, role: str = "member") -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_last_login(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )

    async def update_profile(self, user_id: UUID, **kwargs) -> Optional[User]:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**kwargs, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_by_id(user_id)

    async def verify_email(self, user_id: UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(email_verified=True, updated_at=datetime.now(timezone.utc))
        )

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None


class SessionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, refresh_token_hash: str,
                     expires_at: datetime, device_info: dict = None,
                     ip_address: str = None, user_agent: str = None) -> UserSession:
        session = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_info=device_info or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_token_hash(self, token_hash: str) -> Optional[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_hash: str) -> None:
        await self.db.execute(
            update(UserSession)
            .where(UserSession.refresh_token_hash == token_hash)
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None)
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def cleanup_expired(self) -> int:
        result = await self.db.execute(
            delete(UserSession).where(
                UserSession.expires_at < datetime.now(timezone.utc)
            )
        )
        return result.rowcount


class PasswordResetRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, token_hash: str) -> PasswordResetToken:
        # Invalidate any existing unused tokens for this user
        await self.db.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid(self, token_hash: str) -> Optional[PasswordResetToken]:
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token_id: UUID) -> None:
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
