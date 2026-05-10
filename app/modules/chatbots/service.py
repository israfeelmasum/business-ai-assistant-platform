"""
Chatbots module — business logic.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chatbots.models import (
    Chatbot, ChatbotPersona, ChatbotPrompt,
    ChatbotGuardrail, ChatbotDeployment, ChatbotTheme, ChatbotPrechatForm,
    PromptLayer
)
from app.modules.chatbots.repository import (
    ChatbotRepository, ModelConfigRepository, PersonaRepository,
    PromptRepository, GuardrailRepository, DeploymentRepository,
    ThemeRepository, PrechatFormRepository, _slugify
)
from app.modules.chatbots.schemas import (
    ChatbotCreateRequest, ChatbotUpdateRequest, ChatbotResponse, ChatbotDetailResponse,
    ModelConfigSetRequest, ModelConfigResponse,
    PersonaCreateRequest, PersonaUpdateRequest, PersonaResponse,
    PromptCreateRequest, PromptUpdateRequest, PromptResponse,
    GuardrailCreateRequest, GuardrailUpdateRequest, GuardrailResponse,
    DeploymentCreateRequest, DeploymentUpdateRequest, DeploymentResponse,
    ThemeUpdateRequest, ThemeResponse,
    PrechatFormUpdateRequest, PrechatFormResponse,
)
from app.modules.organizations.repository import MemberRepository
from app.modules.subscriptions.repository import SubscriptionRepository

logger = logging.getLogger(__name__)


class ChatbotService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.bots       = ChatbotRepository(db)
        self.configs    = ModelConfigRepository(db)
        self.personas   = PersonaRepository(db)
        self.prompts    = PromptRepository(db)
        self.guards     = GuardrailRepository(db)
        self.deploys    = DeploymentRepository(db)
        self.themes     = ThemeRepository(db)
        self.forms      = PrechatFormRepository(db)
        self.members    = MemberRepository(db)
        self.subs       = SubscriptionRepository(db)

    # ── Chatbot CRUD ───────────────────────────────────────────────────────────

    async def create_chatbot(
        self, org_id: UUID, req: ChatbotCreateRequest, creator_id: UUID
    ) -> ChatbotResponse:
        await self._require_admin(org_id, creator_id)

        # Check plan chatbot limit
        sub = await self.subs.get_by_org(org_id)
        if sub and sub.plan.max_chatbots is not None:
            existing = await self.bots.list_org_chatbots(org_id, include_inactive=True)
            if len(existing) >= sub.plan.max_chatbots:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Your plan allows max {sub.plan.max_chatbots} chatbot(s). Upgrade to create more."
                )

        base_slug = req.slug or _slugify(req.name)
        slug = await self.bots.unique_slug(org_id, base_slug)
        bot = await self.bots.create(
            org_id=org_id, name=req.name, slug=slug,
            created_by=creator_id, description=req.description,
            avatar_url=req.avatar_url,
        )
        await self.db.commit()
        await self.db.refresh(bot)
        logger.info(f"Chatbot created: {bot.name} (id={bot.id}) org={org_id}")
        return ChatbotResponse.model_validate(bot)

    async def list_chatbots(
        self, org_id: UUID, requester_id: UUID, include_inactive: bool = False
    ) -> List[ChatbotResponse]:
        await self._require_member(org_id, requester_id)
        bots = await self.bots.list_org_chatbots(org_id, include_inactive)
        return [ChatbotResponse.model_validate(b) for b in bots]

    async def get_chatbot(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> ChatbotDetailResponse:
        await self._require_member(org_id, requester_id)
        bot = await self._get_bot_or_404(chatbot_id, org_id)

        # Gather nested data
        persona = await self.personas.get_active(chatbot_id)
        theme   = await self.themes.get(chatbot_id)
        form    = await self.forms.get(chatbot_id)
        prompts = await self.prompts.list_chatbot_prompts(chatbot_id, active_only=True)
        deploys = await self.deploys.list_chatbot(chatbot_id)

        # Build from scalar fields only — avoids lazy-load of ORM relationships
        base = ChatbotResponse.model_validate(bot)
        resp = ChatbotDetailResponse(
            **base.model_dump(),
            persona        = PersonaResponse.model_validate(persona) if persona else None,
            theme          = ThemeResponse.model_validate(theme) if theme else None,
            prechat_form   = PrechatFormResponse.model_validate(form) if form else None,
            active_prompts = [PromptResponse.model_validate(p) for p in prompts],
            deployments    = [DeploymentResponse.model_validate(d) for d in deploys],
        )
        return resp

    async def update_chatbot(
        self, org_id: UUID, chatbot_id: UUID,
        req: ChatbotUpdateRequest, requester_id: UUID
    ) -> ChatbotResponse:
        await self._require_admin(org_id, requester_id)
        updates = req.model_dump(exclude_unset=True)
        if not updates:
            bot = await self._get_bot_or_404(chatbot_id, org_id)
            return ChatbotResponse.model_validate(bot)
        bot = await self.bots.update(chatbot_id, org_id, **updates)
        await self.db.commit()
        await self.db.refresh(bot)
        return ChatbotResponse.model_validate(bot)

    async def delete_chatbot(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        await self.bots.delete(chatbot_id, org_id)
        await self.db.commit()

    # ── Model Config ───────────────────────────────────────────────────────────

    async def set_model_config(
        self, org_id: UUID, chatbot_id: UUID,
        req: ModelConfigSetRequest, requester_id: UUID
    ) -> ModelConfigResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        cfg = await self.configs.upsert(
            chatbot_id=chatbot_id,
            task=req.task,
            provider_source=req.provider_source,
            provider_id=req.provider_id,
            org_provider_id=req.org_provider_id,
            model_id=req.model_id,
            parameters=req.parameters or {"temperature": 0.7, "max_tokens": 1024},
        )
        await self.db.commit()
        await self.db.refresh(cfg)
        return ModelConfigResponse.model_validate(cfg)

    async def list_model_configs(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> List[ModelConfigResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        configs = await self.configs.list_for_chatbot(chatbot_id)
        return [ModelConfigResponse.model_validate(c) for c in configs]

    # ── Persona ──────────────────────────────────��─────────────────────────────

    async def set_persona(
        self, org_id: UUID, chatbot_id: UUID,
        req: PersonaCreateRequest, requester_id: UUID
    ) -> PersonaResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)

        existing = await self.personas.get_active(chatbot_id)
        if existing:
            updates = req.model_dump(exclude_unset=True)
            persona = await self.personas.update(existing.id, chatbot_id, **updates)
        else:
            persona = await self.personas.create(chatbot_id, **req.model_dump())

        await self.db.commit()
        await self.db.refresh(persona)
        return PersonaResponse.model_validate(persona)

    async def get_persona(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> PersonaResponse:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        persona = await self.personas.get_active(chatbot_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Persona not configured yet")
        return PersonaResponse.model_validate(persona)

    # ── Prompts ────────────────────────────────────────────────────────────────

    async def list_prompts(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID,
        layer: Optional[PromptLayer] = None
    ) -> List[PromptResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        prompts = await self.prompts.list_chatbot_prompts(chatbot_id, layer, active_only=False)
        return [PromptResponse.model_validate(p) for p in prompts]

    async def create_prompt(
        self, org_id: UUID, chatbot_id: UUID,
        req: PromptCreateRequest, creator_id: UUID
    ) -> PromptResponse:
        await self._require_admin(org_id, creator_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        prompt = await self.prompts.create(
            chatbot_id=chatbot_id, created_by=creator_id,
            layer=req.layer, name=req.name, content=req.content,
        )
        await self.db.commit()
        await self.db.refresh(prompt)
        return PromptResponse.model_validate(prompt)

    async def update_prompt(
        self, org_id: UUID, chatbot_id: UUID, prompt_id: UUID,
        req: PromptUpdateRequest, requester_id: UUID
    ) -> PromptResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        prompt = await self.prompts.update(prompt_id, chatbot_id, **updates)
        if not prompt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Prompt not found")
        await self.db.commit()
        await self.db.refresh(prompt)
        return PromptResponse.model_validate(prompt)

    async def delete_prompt(
        self, org_id: UUID, chatbot_id: UUID, prompt_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        await self.prompts.delete(prompt_id, chatbot_id)
        await self.db.commit()

    # ── Guardrails ─────────────────────────────────────────────────────────────

    async def list_guardrails(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> List[GuardrailResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        rules = await self.guards.list_chatbot(chatbot_id, active_only=False)
        return [GuardrailResponse.model_validate(r) for r in rules]

    async def create_guardrail(
        self, org_id: UUID, chatbot_id: UUID,
        req: GuardrailCreateRequest, requester_id: UUID
    ) -> GuardrailResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        rule = await self.guards.create(
            chatbot_id=chatbot_id, name=req.name,
            rule_type=req.rule_type, rule_config=req.rule_config,
        )
        await self.db.commit()
        await self.db.refresh(rule)
        return GuardrailResponse.model_validate(rule)

    async def update_guardrail(
        self, org_id: UUID, chatbot_id: UUID, rule_id: UUID,
        req: GuardrailUpdateRequest, requester_id: UUID
    ) -> GuardrailResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        rule = await self.guards.update(rule_id, chatbot_id, **updates)
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Guardrail not found")
        await self.db.commit()
        return GuardrailResponse.model_validate(rule)

    async def delete_guardrail(
        self, org_id: UUID, chatbot_id: UUID, rule_id: UUID, requester_id: UUID
    ) -> None:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        await self.guards.delete(rule_id, chatbot_id)
        await self.db.commit()

    # ── Deployments ────────────────────────────────────────────────────────────

    async def list_deployments(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> List[DeploymentResponse]:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        deploys = await self.deploys.list_chatbot(chatbot_id)
        return [DeploymentResponse.model_validate(d) for d in deploys]

    async def create_deployment(
        self, org_id: UUID, chatbot_id: UUID,
        req: DeploymentCreateRequest, requester_id: UUID
    ) -> DeploymentResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        dep = await self.deploys.create(
            chatbot_id=chatbot_id, channel=req.channel,
            name=req.name, config=req.config, api_key_id=req.api_key_id,
        )
        await self.db.commit()
        await self.db.refresh(dep)
        return DeploymentResponse.model_validate(dep)

    async def update_deployment(
        self, org_id: UUID, chatbot_id: UUID, dep_id: UUID,
        req: DeploymentUpdateRequest, requester_id: UUID
    ) -> DeploymentResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        dep = await self.deploys.update(dep_id, chatbot_id, **updates)
        if not dep:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Deployment not found")
        await self.db.commit()
        return DeploymentResponse.model_validate(dep)

    # ── Theme ─────────────────────────────────────────────────────────────────���

    async def get_theme(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> ThemeResponse:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        theme = await self.themes.get(chatbot_id)
        if not theme:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Theme not found")
        return ThemeResponse.model_validate(theme)

    async def update_theme(
        self, org_id: UUID, chatbot_id: UUID,
        req: ThemeUpdateRequest, requester_id: UUID
    ) -> ThemeResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        theme = await self.themes.upsert(chatbot_id, **updates)
        await self.db.commit()
        await self.db.refresh(theme)
        return ThemeResponse.model_validate(theme)

    # ── Prechat Form ───────────────────────────────────────────────────────────

    async def get_prechat_form(
        self, org_id: UUID, chatbot_id: UUID, requester_id: UUID
    ) -> PrechatFormResponse:
        await self._require_member(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        form = await self.forms.get(chatbot_id)
        if not form:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Prechat form not found")
        return PrechatFormResponse.model_validate(form)

    async def update_prechat_form(
        self, org_id: UUID, chatbot_id: UUID,
        req: PrechatFormUpdateRequest, requester_id: UUID
    ) -> PrechatFormResponse:
        await self._require_admin(org_id, requester_id)
        await self._get_bot_or_404(chatbot_id, org_id)
        updates = req.model_dump(exclude_unset=True)
        form = await self.forms.upsert(chatbot_id, **updates)
        await self.db.commit()
        await self.db.refresh(form)
        return PrechatFormResponse.model_validate(form)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_bot_or_404(self, chatbot_id: UUID, org_id: UUID) -> Chatbot:
        bot = await self.bots.get_by_id(chatbot_id, org_id)
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Chatbot not found")
        return bot

    async def _require_member(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")

    async def _require_admin(self, org_id: UUID, user_id: UUID) -> None:
        member = await self.members.get_membership(org_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not a member of this organization")
        if member.role not in ("admin",):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admin role required")
