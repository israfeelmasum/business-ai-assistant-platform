"""
Chat module — repository layer.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.chat.models import (
    EndUser, Conversation, Message, Escalation, MessageReaction,
    CannedResponse, AiDecisionLog,
    ConversationStatus, MessageRole, MessageType,
    EscalationTrigger, EscalationStatus
)


class EndUserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self, org_id: UUID, chatbot_id: UUID,
        external_id: Optional[str] = None,
        name: Optional[str] = None, email: Optional[str] = None,
        phone: Optional[str] = None, language: Optional[str] = None,
    ) -> Tuple[EndUser, bool]:
        """Returns (end_user, created)."""
        if external_id:
            result = await self.db.execute(
                select(EndUser).where(
                    EndUser.org_id == org_id,
                    EndUser.chatbot_id == chatbot_id,
                    EndUser.external_id == external_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Update last seen
                existing.last_seen_at = datetime.now(timezone.utc)
                existing.updated_at = datetime.now(timezone.utc)
                if name and not existing.name:
                    existing.name = name
                if email and not existing.email:
                    existing.email = email
                await self.db.flush()
                return existing, False

        user = EndUser(
            org_id=org_id, chatbot_id=chatbot_id,
            external_id=external_id, name=name, email=email,
            phone=phone, language=language,
            last_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(user)
        await self.db.flush()
        return user, True

    async def get_by_id(self, user_id: UUID) -> Optional[EndUser]:
        result = await self.db.execute(
            select(EndUser).where(EndUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_chatbot_users(
        self, org_id: UUID, chatbot_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[EndUser]:
        result = await self.db.execute(
            select(EndUser)
            .where(EndUser.org_id == org_id, EndUser.chatbot_id == chatbot_id)
            .order_by(EndUser.last_seen_at.desc().nullslast())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())


class ConversationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_by_session(
        self, chatbot_id: UUID, org_id: UUID, session_id: str, **kwargs
    ) -> Tuple[Conversation, bool]:
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.chatbot_id == chatbot_id,
                Conversation.session_id == session_id,
                Conversation.status == ConversationStatus.active,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        conv = Conversation(
            chatbot_id=chatbot_id, org_id=org_id, session_id=session_id, **kwargs
        )
        self.db.add(conv)
        await self.db.flush()
        return conv, True

    async def get_by_id(self, conv_id: UUID, org_id: Optional[UUID] = None) -> Optional[Conversation]:
        q = select(Conversation).where(Conversation.id == conv_id)
        if org_id:
            q = q.where(Conversation.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_org_conversations(
        self, org_id: UUID, chatbot_id: Optional[UUID] = None,
        status: Optional[ConversationStatus] = None,
        limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        q = select(Conversation).where(Conversation.org_id == org_id)
        if chatbot_id:
            q = q.where(Conversation.chatbot_id == chatbot_id)
        if status:
            q = q.where(Conversation.status == status)
        q = q.order_by(Conversation.last_message_at.desc().nullslast()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def increment_message_count(self, conv_id: UUID, user_message: bool = False) -> None:
        vals = {
            "message_count": Conversation.message_count + 1,
            "last_message_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        if user_message:
            vals["user_message_count"] = Conversation.user_message_count + 1
        await self.db.execute(
            update(Conversation).where(Conversation.id == conv_id).values(**vals)
        )

    async def update_status(self, conv_id: UUID, status: ConversationStatus) -> None:
        vals = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if status == ConversationStatus.resolved:
            vals["resolved_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(Conversation).where(Conversation.id == conv_id).values(**vals)
        )

    async def set_language(self, conv_id: UUID, language: str) -> None:
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(language_detected=language, updated_at=datetime.now(timezone.utc))
        )

    async def update_assigned_agent(self, conv_id: UUID, agent_id: UUID) -> None:
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(assigned_agent_id=agent_id, updated_at=datetime.now(timezone.utc))
        )


class MessageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, conversation_id: UUID, org_id: UUID,
        role: MessageRole, content: str,
        type: MessageType = MessageType.text,
        **kwargs
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            org_id=org_id,
            role=role,
            type=type,
            content=content,
            **kwargs,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_conversation_history(
        self, conv_id: UUID, limit: int = 50
    ) -> List[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        msgs = list(result.scalars().all())
        msgs.reverse()
        return msgs

    async def add_reaction(
        self, message_id: UUID, reaction: str, comment: Optional[str] = None
    ) -> MessageReaction:
        r = MessageReaction(message_id=message_id, reaction=reaction, comment=comment)
        self.db.add(r)
        await self.db.flush()
        return r


class EscalationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, conversation_id: UUID, org_id: UUID,
        trigger: EscalationTrigger, **kwargs
    ) -> Escalation:
        esc = Escalation(
            conversation_id=conversation_id, org_id=org_id,
            trigger=trigger, **kwargs,
        )
        self.db.add(esc)
        await self.db.flush()
        return esc

    async def get_by_id(self, esc_id: UUID, org_id: Optional[UUID] = None) -> Optional[Escalation]:
        q = select(Escalation).where(Escalation.id == esc_id)
        if org_id:
            q = q.where(Escalation.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_active(self, conv_id: UUID) -> Optional[Escalation]:
        result = await self.db.execute(
            select(Escalation).where(
                Escalation.conversation_id == conv_id,
                Escalation.status.in_([EscalationStatus.pending, EscalationStatus.active]),
            ).order_by(Escalation.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_org(
        self, org_id: UUID,
        status: Optional[EscalationStatus] = None,
        chatbot_id: Optional[UUID] = None,
        limit: int = 50, offset: int = 0,
    ) -> List[Escalation]:
        q = (
            select(Escalation)
            .join(Conversation, Conversation.id == Escalation.conversation_id)
            .where(Escalation.org_id == org_id)
        )
        if status:
            q = q.where(Escalation.status == status)
        if chatbot_id:
            q = q.where(Conversation.chatbot_id == chatbot_id)
        q = q.order_by(Escalation.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_org_pending(self, org_id: UUID) -> List[Escalation]:
        result = await self.db.execute(
            select(Escalation).where(
                Escalation.org_id == org_id,
                Escalation.status == EscalationStatus.pending,
            ).order_by(Escalation.created_at)
        )
        return list(result.scalars().all())

    async def list_overdue(self, org_id: UUID) -> List[Escalation]:
        """Escalations past their SLA deadline and not yet resolved."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Escalation).where(
                Escalation.org_id == org_id,
                Escalation.status.in_([EscalationStatus.pending, EscalationStatus.active]),
                Escalation.sla_deadline <= now,
            ).order_by(Escalation.sla_deadline)
        )
        return list(result.scalars().all())

    async def assign(self, esc_id: UUID, agent_id: UUID) -> None:
        await self.db.execute(
            update(Escalation)
            .where(Escalation.id == esc_id)
            .values(
                assigned_agent_id=agent_id,
                assigned_at=datetime.now(timezone.utc),
                status=EscalationStatus.active,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def resolve(
        self, esc_id: UUID, resolved_by: UUID, notes: Optional[str] = None
    ) -> None:
        await self.db.execute(
            update(Escalation)
            .where(Escalation.id == esc_id)
            .values(
                status=EscalationStatus.resolved,
                resolved_at=datetime.now(timezone.utc),
                resolved_by=resolved_by,
                resolution_notes=notes,
                updated_at=datetime.now(timezone.utc),
            )
        )


class CannedResponseRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, org_id: UUID, title: str, content: str,
        chatbot_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
    ) -> CannedResponse:
        cr = CannedResponse(
            org_id=org_id, title=title, content=content,
            chatbot_id=chatbot_id, tags=tags or [],
            created_by=created_by,
        )
        self.db.add(cr)
        await self.db.flush()
        return cr

    async def get_by_id(self, cr_id: UUID, org_id: UUID) -> Optional[CannedResponse]:
        result = await self.db.execute(
            select(CannedResponse).where(
                CannedResponse.id == cr_id,
                CannedResponse.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_org(
        self, org_id: UUID, chatbot_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ) -> List[CannedResponse]:
        from sqlalchemy import or_
        q = select(CannedResponse).where(CannedResponse.org_id == org_id)
        if chatbot_id:
            q = q.where(
                or_(CannedResponse.chatbot_id == chatbot_id, CannedResponse.chatbot_id.is_(None))
            )
        if search:
            q = q.where(
                or_(
                    CannedResponse.title.ilike(f"%{search}%"),
                    CannedResponse.content.ilike(f"%{search}%"),
                )
            )
        q = q.order_by(CannedResponse.title).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(
        self, cr_id: UUID, org_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        chatbot_id: Optional[UUID] = None,
    ) -> Optional[CannedResponse]:
        cr = await self.get_by_id(cr_id, org_id)
        if not cr:
            return None
        if title is not None:
            cr.title = title
        if content is not None:
            cr.content = content
        if tags is not None:
            cr.tags = tags
        if chatbot_id is not None:
            cr.chatbot_id = chatbot_id
        cr.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return cr

    async def delete(self, cr_id: UUID, org_id: UUID) -> bool:
        cr = await self.get_by_id(cr_id, org_id)
        if not cr:
            return False
        await self.db.delete(cr)
        await self.db.flush()
        return True


class DecisionLogRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> AiDecisionLog:
        log = AiDecisionLog(**kwargs)
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_org(
        self, org_id: UUID, chatbot_id: Optional[UUID] = None,
        limit: int = 100, offset: int = 0
    ) -> List[AiDecisionLog]:
        q = select(AiDecisionLog).where(AiDecisionLog.org_id == org_id)
        if chatbot_id:
            q = q.where(AiDecisionLog.chatbot_id == chatbot_id)
        q = q.order_by(AiDecisionLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())
