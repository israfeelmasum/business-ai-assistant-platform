"""
Escalation module — business logic.
Handles agent assignment, SLA monitoring, agent messaging, canned responses.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import (
    MessageRole, MessageType, ConversationStatus, EscalationStatus
)
from app.modules.chat.repository import (
    ConversationRepository, MessageRepository,
    EscalationRepository, CannedResponseRepository
)
from app.modules.chat.schemas import (
    ConversationResponse, MessageResponse, EscalationResponse
)
from app.modules.escalation.schemas import (
    EscalationDetailResponse, CannedResponseResponse,
    AssignEscalationRequest, ResolveEscalationRequest, AgentMessageRequest,
    CreateCannedResponseRequest, UpdateCannedResponseRequest,
)
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)


class EscalationService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.escs       = EscalationRepository(db)
        self.convs      = ConversationRepository(db)
        self.msgs       = MessageRepository(db)
        self.canned     = CannedResponseRepository(db)
        self.members    = MemberRepository(db)

    # ── Auth helper ────────────────────────────────────────────────────────────

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )

    # ── List / Get ─────────────────────────────────────────────────────────────

    async def list_escalations(
        self,
        org_id: UUID,
        requester_id: UUID,
        esc_status: Optional[EscalationStatus] = None,
        chatbot_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EscalationResponse]:
        await self._require_member(org_id, requester_id)
        escs = await self.escs.list_org(
            org_id, status=esc_status, chatbot_id=chatbot_id,
            limit=limit, offset=offset,
        )
        return [EscalationResponse.model_validate(e) for e in escs]

    async def list_overdue(
        self, org_id: UUID, requester_id: UUID
    ) -> List[EscalationResponse]:
        await self._require_member(org_id, requester_id)
        escs = await self.escs.list_overdue(org_id)
        return [EscalationResponse.model_validate(e) for e in escs]

    async def get_detail(
        self, org_id: UUID, esc_id: UUID, requester_id: UUID
    ) -> EscalationDetailResponse:
        await self._require_member(org_id, requester_id)
        esc = await self.escs.get_by_id(esc_id, org_id)
        if not esc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Escalation not found")

        conv = await self.convs.get_by_id(esc.conversation_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Conversation not found")

        messages = await self.msgs.get_conversation_history(conv.id, limit=200)

        now = datetime.now(timezone.utc)
        is_overdue = (
            esc.sla_deadline is not None
            and esc.sla_deadline <= now
            and esc.status in (EscalationStatus.pending, EscalationStatus.active)
        )

        return EscalationDetailResponse(
            escalation=EscalationResponse.model_validate(esc),
            conversation=ConversationResponse.model_validate(conv),
            messages=[MessageResponse.model_validate(m) for m in messages],
            is_overdue=is_overdue,
        )

    # ── Assign ─────────────────────────────────────────────────────────────────

    async def assign(
        self,
        org_id: UUID,
        esc_id: UUID,
        req: AssignEscalationRequest,
        requester_id: UUID,
    ) -> EscalationResponse:
        await self._require_member(org_id, requester_id)

        esc = await self.escs.get_by_id(esc_id, org_id)
        if not esc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Escalation not found")
        if esc.status == EscalationStatus.resolved:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Escalation already resolved")

        # Verify agent is a member of the org
        agent_member = await self.members.get_membership(org_id, req.agent_id)
        if not agent_member:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Agent is not a member of this organization")

        await self.escs.assign(esc_id, req.agent_id)
        # Also assign on the conversation
        await self.convs.update_assigned_agent(esc.conversation_id, req.agent_id)
        await self.db.commit()

        updated = await self.escs.get_by_id(esc_id, org_id)
        return EscalationResponse.model_validate(updated)

    # ── Resolve ────────────────────────────────────────────────────────────────

    async def resolve(
        self,
        org_id: UUID,
        esc_id: UUID,
        req: ResolveEscalationRequest,
        requester_id: UUID,
    ) -> None:
        await self._require_member(org_id, requester_id)

        esc = await self.escs.get_by_id(esc_id, org_id)
        if not esc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Escalation not found")
        if esc.status == EscalationStatus.resolved:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Escalation already resolved")

        await self.escs.resolve(esc_id, resolved_by=requester_id, notes=req.notes)
        await self.convs.update_status(esc.conversation_id, ConversationStatus.resolved)
        await self.db.commit()

    # ── Agent sends message ────────────────────────────────────────────────────

    async def send_agent_message(
        self,
        org_id: UUID,
        esc_id: UUID,
        req: AgentMessageRequest,
        agent_id: UUID,
    ) -> MessageResponse:
        await self._require_member(org_id, agent_id)

        esc = await self.escs.get_by_id(esc_id, org_id)
        if not esc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Escalation not found")
        if esc.status == EscalationStatus.resolved:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Escalation is already resolved")

        msg = await self.msgs.create(
            conversation_id=esc.conversation_id,
            org_id=org_id,
            role=MessageRole.agent,
            content=req.content,
            type=MessageType.text,
            agent_id=agent_id,
        )
        await self.convs.increment_message_count(esc.conversation_id)
        await self.db.commit()
        return MessageResponse.model_validate(msg)

    # ── Canned Responses ───────────────────────────────────────────────────────

    async def list_canned(
        self,
        org_id: UUID,
        requester_id: UUID,
        chatbot_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CannedResponseResponse]:
        await self._require_member(org_id, requester_id)
        items = await self.canned.list_org(org_id, chatbot_id=chatbot_id,
                                           search=search, limit=limit, offset=offset)
        return [CannedResponseResponse.model_validate(c) for c in items]

    async def create_canned(
        self,
        org_id: UUID,
        req: CreateCannedResponseRequest,
        requester_id: UUID,
    ) -> CannedResponseResponse:
        await self._require_member(org_id, requester_id)
        cr = await self.canned.create(
            org_id=org_id,
            title=req.title,
            content=req.content,
            chatbot_id=req.chatbot_id,
            tags=req.tags,
            created_by=requester_id,
        )
        await self.db.commit()
        return CannedResponseResponse.model_validate(cr)

    async def update_canned(
        self,
        org_id: UUID,
        cr_id: UUID,
        req: UpdateCannedResponseRequest,
        requester_id: UUID,
    ) -> CannedResponseResponse:
        await self._require_member(org_id, requester_id)
        cr = await self.canned.update(
            cr_id, org_id,
            title=req.title,
            content=req.content,
            tags=req.tags,
            chatbot_id=req.chatbot_id,
        )
        if not cr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Canned response not found")
        await self.db.commit()
        return CannedResponseResponse.model_validate(cr)

    async def delete_canned(
        self, org_id: UUID, cr_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_member(org_id, requester_id)
        deleted = await self.canned.delete(cr_id, org_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Canned response not found")
        await self.db.commit()
