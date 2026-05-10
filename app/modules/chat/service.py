"""
Chat module — business logic service.
Orchestrates the chat engine, conversation management, escalation.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.engine import ChatEngine, EscalationTrigger
from app.modules.chat.models import (
    Conversation, Message, EndUser,
    MessageRole, MessageType, ConversationStatus, EscalationStatus
)
from app.modules.chat.repository import (
    EndUserRepository, ConversationRepository, MessageRepository,
    EscalationRepository, DecisionLogRepository
)
from app.modules.chat.schemas import (
    StartChatRequest, SendMessageRequest,
    ConversationResponse, MessageResponse, ConversationHistoryResponse,
    EndUserResponse, EscalationResponse, ReactMessageRequest,
)
from app.modules.chatbots.repository import (
    ChatbotRepository, ModelConfigRepository, PersonaRepository,
    PromptRepository, GuardrailRepository
)
from app.modules.knowledge.repository import KBRepository
from app.modules.ai_providers.service import AiProviderService
from app.modules.ai_providers.models import ModelCapability
from app.modules.tokens.service import TokenService
from app.modules.tokens.models import TokenAction
from app.modules.tokens.schemas import DebitTokensRequest
from app.modules.organizations.repository import MemberRepository

logger = logging.getLogger(__name__)

SLA_DEFAULT_MINUTES = 30


class ChatService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.end_users  = EndUserRepository(db)
        self.convs      = ConversationRepository(db)
        self.msgs       = MessageRepository(db)
        self.escalations = EscalationRepository(db)
        self.decision_logs = DecisionLogRepository(db)
        self.chatbots   = ChatbotRepository(db)
        self.configs    = ModelConfigRepository(db)
        self.personas   = PersonaRepository(db)
        self.prompts    = PromptRepository(db)
        self.guards     = GuardrailRepository(db)
        self.kbs        = KBRepository(db)
        self.members    = MemberRepository(db)
        self.ai_svc     = AiProviderService(db)
        self.token_svc  = TokenService(db)

    # ── Start / Resume Conversation ────────────────────────────────────────────

    async def start_or_resume(self, req: StartChatRequest) -> ConversationResponse:
        chatbot = await self.chatbots.get_by_id(req.chatbot_id)
        if not chatbot or not chatbot.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Chatbot not found or inactive")

        # Resolve end user
        end_user, _ = await self.end_users.get_or_create(
            org_id=chatbot.org_id,
            chatbot_id=req.chatbot_id,
            external_id=req.external_id,
            name=req.user_info.get("name") if req.user_info else None,
            email=req.user_info.get("email") if req.user_info else None,
            language=req.language,
        )

        # Get or create conversation
        conv, created = await self.convs.get_or_create_by_session(
            chatbot_id=req.chatbot_id,
            org_id=chatbot.org_id,
            session_id=req.session_id,
            end_user_id=end_user.id,
            channel=req.channel,
            user_info=req.user_info or {},
            prechat_data=req.prechat_data or {},
            utm_source=req.utm_source,
            utm_medium=req.utm_medium,
            referrer_url=req.referrer_url,
            user_agent=req.user_agent,
            language_detected=req.language,
        )

        if created:
            # Increment user conversation count
            end_user.total_conversations += 1
            await self.db.flush()

        await self.db.commit()
        return ConversationResponse.model_validate(conv)

    # ── Stream Chat ────────────────────────────────────────────────────────────

    async def stream_chat(
        self,
        session_id: str,
        req: SendMessageRequest,
        chatbot_id: UUID,
    ) -> AsyncIterator[str]:
        """
        Main streaming endpoint. Yields raw SSE lines.
        DB commit happens after streaming completes.
        """
        # ── Validate chatbot ───────────────────────────────────────────────────
        chatbot = await self.chatbots.get_by_id(chatbot_id)
        if not chatbot or not chatbot.is_active:
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Chatbot not found'})}\n\n"
            return

        org_id = chatbot.org_id

        # ── Token quota check ──────────────────────────────────────────────────
        has_quota = await self.token_svc.check_quota(org_id, TokenAction.chat_message)
        if not has_quota:
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Token quota exceeded. Please top up.'})}\n\n"
            return

        # ── Get / resume conversation ──────────────────────────────────────────
        conv = await self._get_conv_by_session(session_id, chatbot_id)
        if not conv:
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Conversation not found. Start a session first.'})}\n\n"
            return

        if conv.status not in (ConversationStatus.active,):
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Conversation is not active.'})}\n\n"
            return

        # ── Load chatbot config ────────────────────────────────────────────────
        chatbot_config = await self._build_chatbot_config(chatbot, org_id)

        # ── Load conversation history into config ──────────────────────────────
        history_msgs = await self.msgs.get_conversation_history(conv.id, limit=20)
        chatbot_config["message_history"] = [
            {"role": m.role.value, "content": m.content or ""}
            for m in history_msgs
            if m.content and m.role.value in ("user", "assistant")
        ]

        # ── Auto-detect language (every message) ───────────────────────────────
        if req.content:
            from app.modules.language.detector import detect_language
            detected_lang = detect_language(req.content)
            # Only store non-English detections; keep previous if current msg is English
            if detected_lang != "en":
                await self.convs.set_language(conv.id, detected_lang)
                chatbot_config["language"] = detected_lang
            elif conv.language_detected and conv.language_detected != "en":
                # User switched back to English — honour it
                chatbot_config["language"] = "en"
                await self.convs.set_language(conv.id, "en")

        # ── Store user message ─────────────────────────────────────────────────
        user_msg = await self.msgs.create(
            conversation_id=conv.id, org_id=org_id,
            role=MessageRole.user, content=req.content, type=req.type,
            attachments=req.attachments or [],
        )
        await self.convs.increment_message_count(conv.id, user_message=True)
        await self.db.flush()

        # ── Resolve provider ───────────────────────────────────────────────────
        model_config = await self.configs.get_for_task(chatbot.id, "chat")
        provider_config = await self.ai_svc.resolve_provider_key(
            org_id=org_id,
            capability=ModelCapability.chat,
            org_provider_id=model_config.org_provider_id if model_config else None,
        )
        embedding_model_config = await self.configs.get_for_task(chatbot.id, "embedding")
        embedding_config = await self.ai_svc.resolve_provider_key(
            org_id=org_id,
            capability=ModelCapability.embedding,
            org_provider_id=embedding_model_config.org_provider_id if embedding_model_config else None,
        )
        if model_config:
            chatbot_config["model_id"] = model_config.model_id
            chatbot_config["parameters"] = model_config.parameters or {}
        if embedding_model_config:
            chatbot_config["embedding_model"] = embedding_model_config.model_id

        # ── Load fallback contacts from chatbot theme ──────────────────────────
        fallback_contacts = None
        if chatbot.theme:
            t = chatbot.theme
            fallback_contacts = {
                "whatsapp": t.fallback_whatsapp,
                "email": t.fallback_email,
                "phone": t.fallback_phone,
                "message": t.fallback_message or "Our team is here to help. Reach us via:",
            }

        # ── Streaming ──────────────────────────────────────────────────────────
        engine = ChatEngine(self.db)
        assistant_content = ""
        internal_data = None

        async for chunk in engine.process_message(
            conversation=conv,
            user_content=req.content,
            chatbot_config=chatbot_config,
            provider_config=provider_config,
            embedding_config={**embedding_config, "model_id": chatbot_config.get("embedding_model", "nomic-embed-text")},
            image_base64=req.image_base64,
            fallback_contacts=fallback_contacts,
        ):
            # The last yielded item is the internal data dict (not SSE)
            if chunk.startswith('{"_internal":'):
                internal_data = json.loads(chunk)
            else:
                yield chunk

        # ── Post-stream: store assistant message + audit log ───────────────────
        if internal_data:
            assistant_msg = await self.msgs.create(
                conversation_id=conv.id, org_id=org_id,
                role=MessageRole.assistant, content=internal_data["full_response"],
                model_used=internal_data["model_used"],
                tokens_input=internal_data["tokens_input"],
                tokens_output=internal_data["tokens_output"],
                latency_ms=internal_data["latency_ms"],
                confidence=internal_data["confidence"],
                eil_score=internal_data["eil_score"],
                rag_sources=internal_data["rag_sources"],
                trace_id=uuid.UUID(internal_data["trace_id"]),
            )
            await self.convs.increment_message_count(conv.id)

            # AI Decision Log
            await self.decision_logs.create(
                trace_id=uuid.UUID(internal_data["trace_id"]),
                message_id=assistant_msg.id,
                conversation_id=conv.id,
                chatbot_id=chatbot.id,
                org_id=org_id,
                system_prompt_snapshot=internal_data.get("system_prompt_snapshot", ""),
                retrieved_context=internal_data["rag_sources"],
                user_message=req.content,
                ai_response=internal_data["full_response"],
                model_used=internal_data["model_used"],
                provider_type=internal_data["provider_type"],
                tokens_input=internal_data["tokens_input"],
                tokens_output=internal_data["tokens_output"],
                confidence=internal_data["confidence"],
                eil_score=internal_data["eil_score"],
                vector_search_ms=internal_data["vector_search_ms"],
                llm_ttft_ms=internal_data["llm_ttft_ms"],
                total_latency_ms=internal_data["latency_ms"],
                was_escalated=internal_data.get("should_escalate", False),
            )

            # Auto-escalate if needed
            if internal_data.get("should_escalate") and internal_data.get("escalation_trigger"):
                trigger = EscalationTrigger(internal_data["escalation_trigger"])
                await self._trigger_escalation(conv, org_id, trigger)

            # Debit tokens
            try:
                await self.token_svc.debit_tokens(
                    org_id=org_id,
                    req=DebitTokensRequest(
                        action=TokenAction.chat_message,
                        tokens=max(1, (internal_data["tokens_input"] + internal_data["tokens_output"]) // 10),
                        chatbot_id=chatbot.id,
                        reference_id=assistant_msg.id,
                        model_used=internal_data["model_used"],
                    )
                )
            except Exception as e:
                logger.warning(f"Token debit failed (non-fatal): {e}")

            await self.db.commit()

    # ── Conversation History ───────────────────────────────────────────────────

    async def get_history(
        self, session_id: str, chatbot_id: UUID
    ) -> ConversationHistoryResponse:
        conv = await self._get_conv_by_session(session_id, chatbot_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Conversation not found")
        messages = await self.msgs.get_conversation_history(conv.id)
        escalation = await self.escalations.get_active(conv.id)

        return ConversationHistoryResponse(
            conversation=ConversationResponse.model_validate(conv),
            messages=[MessageResponse.model_validate(m) for m in messages],
            escalation=EscalationResponse.model_validate(escalation) if escalation else None,
        )

    # ── Admin: list conversations ──────────────────────────────────────────────

    async def list_conversations(
        self, org_id: UUID, requester_id: UUID,
        chatbot_id: Optional[UUID] = None,
        conv_status: Optional[ConversationStatus] = None,
        limit: int = 50, offset: int = 0
    ) -> List[ConversationResponse]:
        await self._require_member(org_id, requester_id)
        convs = await self.convs.list_org_conversations(
            org_id, chatbot_id, conv_status, limit, offset
        )
        return [ConversationResponse.model_validate(c) for c in convs]

    async def resolve_conversation(
        self, org_id: UUID, conv_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_member(org_id, requester_id)
        await self.convs.update_status(conv_id, ConversationStatus.resolved)
        await self.db.commit()

    # ── Reaction ───────────────────────────────────────────────────────────────

    async def react_to_message(
        self, message_id: UUID, req: ReactMessageRequest
    ) -> None:
        await self.msgs.add_reaction(message_id, req.reaction, req.comment)
        await self.db.commit()

    # ── End Users ──────────────────────────────────────────────────────────────

    async def list_end_users(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID,
        limit: int = 100, offset: int = 0
    ) -> List[EndUserResponse]:
        await self._require_member(org_id, requester_id)
        users = await self.end_users.list_chatbot_users(org_id, chatbot_id, limit, offset)
        return [EndUserResponse.model_validate(u) for u in users]

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_conv_by_session(
        self, session_id: str, chatbot_id: UUID
    ) -> Optional[Conversation]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.chatbot_id == chatbot_id,
                Conversation.status == ConversationStatus.active,
            ).order_by(Conversation.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _build_chatbot_config(self, chatbot, org_id: UUID) -> dict:
        """Load all chatbot config into a single dict for the engine."""
        from app.modules.organizations.repository import OrganizationRepository
        org_repo = OrganizationRepository(self.db)
        org = await org_repo.get_by_id(org_id)

        persona = await self.personas.get_active(chatbot.id)
        prompts = await self.prompts.list_chatbot_prompts(chatbot.id, active_only=True)
        guardrails = await self.guards.list_chatbot(chatbot.id, active_only=True)
        kbs = await self.kbs.list_chatbot(chatbot.id)
        active_kbs = [kb for kb in kbs if kb.is_active]

        return {
            "persona_name": persona.persona_name if persona else "Assistant",
            "personality": persona.personality.value if persona else "professional",
            "domain": persona.domain.value if persona else "general",
            "language": persona.default_language if persona else "en",
            "fallback_behavior": persona.fallback_behavior.value if persona else "escalate",
            "org_name": org.name if org else "",
            "model_id": "llama3.2",  # overridden by model_config if set
            "parameters": {"temperature": 0.7, "max_tokens": 1024},
            "prompts": [{"layer": p.layer.value, "content": p.content} for p in prompts],
            "guardrails": [{"is_active": g.is_active, "rule_config": g.rule_config} for g in guardrails],
            # Multi-KB: pass ALL active KB IDs for parallel search
            "knowledge_base_ids": [kb.id for kb in active_kbs],
            "knowledge_base_id": active_kbs[0].id if active_kbs else None,  # legacy compat
            "rag_top_k": 5,
            "rag_threshold": 0.7,
            "embedding_model": "nomic-embed-text",
            "message_history": [],  # populated in stream_chat before engine call
        }

    async def _trigger_escalation(
        self, conv: Conversation, org_id: UUID, trigger: EscalationTrigger
    ) -> None:
        existing = await self.escalations.get_active(conv.id)
        if existing:
            return  # already escalated

        sla_deadline = datetime.now(timezone.utc) + timedelta(minutes=SLA_DEFAULT_MINUTES)
        await self.escalations.create(
            conversation_id=conv.id,
            org_id=org_id,
            trigger=trigger,
            sla_minutes=SLA_DEFAULT_MINUTES,
            sla_deadline=sla_deadline,
        )
        await self.convs.update_status(conv.id, ConversationStatus.human_escalated)

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
