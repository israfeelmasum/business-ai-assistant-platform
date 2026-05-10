"""
Tokens router — packages, balance, ledger, usage metering.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User, UserRole
from app.modules.tokens.schemas import (
    TokenPackageResponse, CreateTokenPackageRequest,
    TokenLedgerEntry, OrgTokenBalance,
    UsageRecordResponse
)
from app.modules.tokens.service import TokenService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tokens"])


# ── Token Packages (public read, super_admin write) ────────────────────────────

@router.get("/token-packages", response_model=List[TokenPackageResponse])
async def list_token_packages(db: AsyncSession = Depends(get_db)):
    """List all active token top-up packages (public)."""
    svc = TokenService(db)
    return await svc.list_packages()


@router.post(
    "/token-packages",
    response_model=TokenPackageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.super_admin))],
)
async def create_token_package(
    req: CreateTokenPackageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a token top-up package. Super-admin only."""
    svc = TokenService(db)
    return await svc.create_package(req)


@router.delete(
    "/token-packages/{pkg_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.super_admin))],
)
async def deactivate_token_package(
    pkg_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a token package. Super-admin only."""
    svc = TokenService(db)
    await svc.deactivate_package(pkg_id)


# ── Org Token Balance ──────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/tokens/balance", response_model=OrgTokenBalance)
async def get_token_balance(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current token balance for an organization."""
    svc = TokenService(db)
    return await svc.get_balance(org_id, requester_id=current_user.id)


# ── Token Ledger ───────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/tokens/ledger", response_model=List[TokenLedgerEntry])
async def get_token_ledger(
    org_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get token transaction history for an organization."""
    svc = TokenService(db)
    return await svc.get_ledger(org_id, requester_id=current_user.id,
                                limit=limit, offset=offset)


# ── Usage Records ──────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/tokens/usage", response_model=List[UsageRecordResponse])
async def get_usage_history(
    org_id: UUID,
    limit: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get monthly usage history (last 12 months by default)."""
    svc = TokenService(db)
    return await svc.get_usage(org_id, requester_id=current_user.id, limit=limit)


@router.get("/organizations/{org_id}/tokens/usage/current", response_model=List[UsageRecordResponse])
async def get_current_usage(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage for the current billing month."""
    svc = TokenService(db)
    return await svc.get_current_usage(org_id, requester_id=current_user.id)
