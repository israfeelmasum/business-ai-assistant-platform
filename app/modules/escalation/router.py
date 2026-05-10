"""
Escalation module — router.

All endpoints require JWT authentication (agent console / admin only).

Escalation endpoints:
  GET    /organizations/{org_id}/escalations              — list escalations
  GET    /organizations/{org_id}/escalations/overdue      — SLA-breached
  GET    /organizations/{org_id}/escalations/{id}         — detail + conversation
  PATCH  /organizations/{org_id}/escalations/{id}/assign  — assign to agent
  PATCH  /organizations/{org_id}/escalations/{id}/resolve — mark resolved
  POST   /organizations/{org_id}/escalations/{id}/messages — agent reply

Canned Response endpoints:
  GET    /organizations/{org_id}/canned-responses         — list
  POST   /organizations/{org_id}/canned-responses         — create
  PATCH  /organizations/{org_id}/canned-responses/{id}    — update
  DELETE /organizations/{org_id}/canned-responses/{id}    — delete
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.models import EscalationStatus
from app.modules.chat.schemas import EscalationResponse, MessageResponse
from app.modules.escalation.schemas import (
    EscalationDetailResponse,
    AssignEscalationRequest, ResolveEscalationRequest, AgentMessageRequest,
    CannedResponseResponse, CreateCannedResponseRequest, UpdateCannedResponseRequest,
)
from app.modules.escalation.service import EscalationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Escalation & Agent Console"])


# ── Escalation endpoints ───────────────────────────────────────────────────────

@router.get(
    "/organizations/{org_id}/escalations",
    response_model=List[EscalationResponse],
)
async def list_escalations(
    org_id: UUID,
    esc_status: Optional[EscalationStatus] = Query(None, alias="status"),
    chatbot_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List escalations for an organization. Filter by status or chatbot."""
    svc = EscalationService(db)
    return await svc.list_escalations(
        org_id, requester_id=current_user.id,
        esc_status=esc_status, chatbot_id=chatbot_id,
        limit=limit, offset=offset,
    )


@router.get(
    "/organizations/{org_id}/escalations/overdue",
    response_model=List[EscalationResponse],
)
async def list_overdue_escalations(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all escalations that have breached their SLA deadline."""
    svc = EscalationService(db)
    return await svc.list_overdue(org_id, requester_id=current_user.id)


@router.get(
    "/organizations/{org_id}/escalations/{esc_id}",
    response_model=EscalationDetailResponse,
)
async def get_escalation_detail(
    org_id: UUID,
    esc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full escalation detail — includes the conversation record + all messages.
    Used by the agent console to render the live chat view.
    """
    svc = EscalationService(db)
    return await svc.get_detail(org_id, esc_id, requester_id=current_user.id)


@router.patch(
    "/organizations/{org_id}/escalations/{esc_id}/assign",
    response_model=EscalationResponse,
)
async def assign_escalation(
    org_id: UUID,
    esc_id: UUID,
    req: AssignEscalationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assign an escalated conversation to a human agent.
    The agent must be a member of the organization.
    Transitions status: pending → active.
    """
    svc = EscalationService(db)
    return await svc.assign(org_id, esc_id, req, requester_id=current_user.id)


@router.patch(
    "/organizations/{org_id}/escalations/{esc_id}/resolve",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def resolve_escalation(
    org_id: UUID,
    esc_id: UUID,
    req: ResolveEscalationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark an escalation as resolved. Optionally provide resolution notes.
    Also marks the parent conversation as resolved.
    """
    svc = EscalationService(db)
    await svc.resolve(org_id, esc_id, req, requester_id=current_user.id)


@router.post(
    "/organizations/{org_id}/escalations/{esc_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def agent_send_message(
    org_id: UUID,
    esc_id: UUID,
    req: AgentMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Agent sends a message in an escalated conversation.
    Message is stored with role=agent and linked to the conversation.
    """
    svc = EscalationService(db)
    return await svc.send_agent_message(org_id, esc_id, req, agent_id=current_user.id)


# ── Canned Responses ───────────────────────────────────────────────────────────

@router.get(
    "/organizations/{org_id}/canned-responses",
    response_model=List[CannedResponseResponse],
)
async def list_canned_responses(
    org_id: UUID,
    chatbot_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List canned responses for an org. Optional chatbot filter + text search."""
    svc = EscalationService(db)
    return await svc.list_canned(
        org_id, requester_id=current_user.id,
        chatbot_id=chatbot_id, search=search,
        limit=limit, offset=offset,
    )


@router.post(
    "/organizations/{org_id}/canned-responses",
    response_model=CannedResponseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_canned_response(
    org_id: UUID,
    req: CreateCannedResponseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new canned response. chatbot_id=null means it applies org-wide."""
    svc = EscalationService(db)
    return await svc.create_canned(org_id, req, requester_id=current_user.id)


@router.patch(
    "/organizations/{org_id}/canned-responses/{cr_id}",
    response_model=CannedResponseResponse,
)
async def update_canned_response(
    org_id: UUID,
    cr_id: UUID,
    req: UpdateCannedResponseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update title, content, tags, or chatbot scope of a canned response."""
    svc = EscalationService(db)
    return await svc.update_canned(org_id, cr_id, req, requester_id=current_user.id)


@router.delete(
    "/organizations/{org_id}/canned-responses/{cr_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_canned_response(
    org_id: UUID,
    cr_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a canned response."""
    svc = EscalationService(db)
    await svc.delete_canned(org_id, cr_id, requester_id=current_user.id)
