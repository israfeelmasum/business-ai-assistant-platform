"""
Chatbots router — full chatbot configuration CRUD.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chatbots.models import PromptLayer
from app.modules.chatbots.schemas import (
    ChatbotCreateRequest, ChatbotUpdateRequest, ChatbotResponse, ChatbotDetailResponse,
    ModelConfigSetRequest, ModelConfigResponse,
    PersonaCreateRequest, PersonaResponse,
    PromptCreateRequest, PromptUpdateRequest, PromptResponse,
    GuardrailCreateRequest, GuardrailUpdateRequest, GuardrailResponse,
    DeploymentCreateRequest, DeploymentUpdateRequest, DeploymentResponse,
    ThemeUpdateRequest, ThemeResponse,
    PrechatFormUpdateRequest, PrechatFormResponse,
    WidgetConfigResponse,
)
from app.modules.chatbots.service import ChatbotService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chatbots"])


# ── Public Widget Config (no auth) ─────────────────────────────────────────────

@router.get("/chat/widget-config", response_model=WidgetConfigResponse, tags=["Chat"])
async def get_widget_config(
    chatbot_id: UUID = Query(..., description="Chatbot UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — returns widget branding, colors, welcome message, and
    fallback contact info for the chat widget to apply on load.
    No authentication required.
    """
    from fastapi import HTTPException
    from sqlalchemy import select as _select
    from app.modules.chatbots.models import Chatbot, ChatbotTheme, ChatbotPersona

    # Load chatbot
    res = await db.execute(_select(Chatbot).where(Chatbot.id == chatbot_id))
    chatbot = res.scalar_one_or_none()
    if not chatbot or not chatbot.is_active:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    # Load theme separately (avoids lazy-load in async context)
    tr = await db.execute(_select(ChatbotTheme).where(ChatbotTheme.chatbot_id == chatbot_id))
    theme = tr.scalar_one_or_none()

    # Load persona separately
    pr = await db.execute(
        _select(ChatbotPersona).where(ChatbotPersona.chatbot_id == chatbot_id).limit(1)
    )
    persona = pr.scalar_one_or_none()

    return WidgetConfigResponse(
        chatbot_id=chatbot.id,
        chatbot_name=chatbot.name,
        color_primary=theme.color_primary if theme else "#2563EB",
        color_user_bubble=theme.color_user_bubble if theme else "#2563EB",
        color_bot_bubble=theme.color_bot_bubble if theme else "#F3F4F6",
        color_background=theme.color_background if theme else "#FFFFFF",
        color_text=theme.color_text if theme else "#111827",
        logo_url=theme.logo_url if theme else None,
        welcome_message=(theme.welcome_message if theme and theme.welcome_message else "Hello! How can I help you today?"),
        persona_name=persona.persona_name if persona else "Assistant",
        greeting_message=persona.greeting_message if persona else None,
        fallback_whatsapp=theme.fallback_whatsapp if theme else None,
        fallback_email=theme.fallback_email if theme else None,
        fallback_phone=theme.fallback_phone if theme else None,
        fallback_message=(theme.fallback_message if theme and theme.fallback_message else "Our team is here to help. Reach us via:"),
        position=theme.position if theme else "bottom-right",
        widget_width=theme.widget_width if theme else 380,
        widget_height=theme.widget_height if theme else 600,
        border_radius=theme.border_radius if theme else 12,
        font_family=theme.font_family if theme else "Inter",
    )


# ── Chatbot CRUD ───────────────────────────────────────────────────────────────

@router.post("/organizations/{org_id}/chatbots",
             response_model=ChatbotResponse,
             status_code=status.HTTP_201_CREATED)
async def create_chatbot(
    org_id: UUID,
    req: ChatbotCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chatbot. Admin only."""
    svc = ChatbotService(db)
    return await svc.create_chatbot(org_id, req, creator_id=current_user.id)


@router.get("/organizations/{org_id}/chatbots", response_model=List[ChatbotResponse])
async def list_chatbots(
    org_id: UUID,
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chatbots for an organization."""
    svc = ChatbotService(db)
    return await svc.list_chatbots(org_id, requester_id=current_user.id,
                                   include_inactive=include_inactive)


@router.get("/organizations/{org_id}/chatbots/{chatbot_id}",
            response_model=ChatbotDetailResponse)
async def get_chatbot(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full chatbot details including persona, theme, prompts, deployments."""
    svc = ChatbotService(db)
    return await svc.get_chatbot(org_id, chatbot_id, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}",
              response_model=ChatbotResponse)
async def update_chatbot(
    org_id: UUID,
    chatbot_id: UUID,
    req: ChatbotUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update chatbot core settings. Admin only."""
    svc = ChatbotService(db)
    return await svc.update_chatbot(org_id, chatbot_id, req, requester_id=current_user.id)


@router.delete("/organizations/{org_id}/chatbots/{chatbot_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a chatbot and all its data. Admin only."""
    svc = ChatbotService(db)
    await svc.delete_chatbot(org_id, chatbot_id, requester_id=current_user.id)


# ── Model Config ───────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/model-configs",
            response_model=List[ModelConfigResponse])
async def list_model_configs(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.list_model_configs(org_id, chatbot_id, requester_id=current_user.id)


@router.put("/organizations/{org_id}/chatbots/{chatbot_id}/model-configs",
            response_model=ModelConfigResponse)
async def set_model_config(
    org_id: UUID,
    chatbot_id: UUID,
    req: ModelConfigSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set (upsert) AI model config for a specific task. Admin only."""
    svc = ChatbotService(db)
    return await svc.set_model_config(org_id, chatbot_id, req, requester_id=current_user.id)


# ── Persona ────────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/persona",
            response_model=PersonaResponse)
async def get_persona(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.get_persona(org_id, chatbot_id, requester_id=current_user.id)


@router.put("/organizations/{org_id}/chatbots/{chatbot_id}/persona",
            response_model=PersonaResponse)
@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}/persona",
              response_model=PersonaResponse)
async def set_persona(
    org_id: UUID,
    chatbot_id: UUID,
    req: PersonaCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set chatbot persona (upsert). Accepts both PUT and PATCH. Admin only."""
    svc = ChatbotService(db)
    return await svc.set_persona(org_id, chatbot_id, req, requester_id=current_user.id)


# ── Prompts ────────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/prompts",
            response_model=List[PromptResponse])
async def list_prompts(
    org_id: UUID,
    chatbot_id: UUID,
    layer: Optional[PromptLayer] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.list_prompts(org_id, chatbot_id, requester_id=current_user.id, layer=layer)


@router.post("/organizations/{org_id}/chatbots/{chatbot_id}/prompts",
             response_model=PromptResponse,
             status_code=status.HTTP_201_CREATED)
async def create_prompt(
    org_id: UUID,
    chatbot_id: UUID,
    req: PromptCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a prompt layer. Admin only."""
    svc = ChatbotService(db)
    return await svc.create_prompt(org_id, chatbot_id, req, creator_id=current_user.id)


@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}/prompts/{prompt_id}",
              response_model=PromptResponse)
async def update_prompt(
    org_id: UUID,
    chatbot_id: UUID,
    prompt_id: UUID,
    req: PromptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.update_prompt(org_id, chatbot_id, prompt_id, req,
                                   requester_id=current_user.id)


@router.delete("/organizations/{org_id}/chatbots/{chatbot_id}/prompts/{prompt_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    org_id: UUID,
    chatbot_id: UUID,
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    await svc.delete_prompt(org_id, chatbot_id, prompt_id, requester_id=current_user.id)


# ── Guardrails ─────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/guardrails",
            response_model=List[GuardrailResponse])
async def list_guardrails(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.list_guardrails(org_id, chatbot_id, requester_id=current_user.id)


@router.post("/organizations/{org_id}/chatbots/{chatbot_id}/guardrails",
             response_model=GuardrailResponse,
             status_code=status.HTTP_201_CREATED)
async def create_guardrail(
    org_id: UUID,
    chatbot_id: UUID,
    req: GuardrailCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.create_guardrail(org_id, chatbot_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}/guardrails/{rule_id}",
              response_model=GuardrailResponse)
async def update_guardrail(
    org_id: UUID,
    chatbot_id: UUID,
    rule_id: UUID,
    req: GuardrailUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.update_guardrail(org_id, chatbot_id, rule_id, req,
                                      requester_id=current_user.id)


@router.delete("/organizations/{org_id}/chatbots/{chatbot_id}/guardrails/{rule_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(
    org_id: UUID,
    chatbot_id: UUID,
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    await svc.delete_guardrail(org_id, chatbot_id, rule_id, requester_id=current_user.id)


# ── Deployments ────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/deployments",
            response_model=List[DeploymentResponse])
async def list_deployments(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.list_deployments(org_id, chatbot_id, requester_id=current_user.id)


@router.post("/organizations/{org_id}/chatbots/{chatbot_id}/deployments",
             response_model=DeploymentResponse,
             status_code=status.HTTP_201_CREATED)
async def create_deployment(
    org_id: UUID,
    chatbot_id: UUID,
    req: DeploymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.create_deployment(org_id, chatbot_id, req, requester_id=current_user.id)


@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}/deployments/{dep_id}",
              response_model=DeploymentResponse)
async def update_deployment(
    org_id: UUID,
    chatbot_id: UUID,
    dep_id: UUID,
    req: DeploymentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.update_deployment(org_id, chatbot_id, dep_id, req,
                                       requester_id=current_user.id)


# ── Theme ──────────────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/theme",
            response_model=ThemeResponse)
async def get_theme(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.get_theme(org_id, chatbot_id, requester_id=current_user.id)


@router.put("/organizations/{org_id}/chatbots/{chatbot_id}/theme",
            response_model=ThemeResponse)
@router.patch("/organizations/{org_id}/chatbots/{chatbot_id}/theme",
              response_model=ThemeResponse)
async def update_theme(
    org_id: UUID,
    chatbot_id: UUID,
    req: ThemeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update chatbot theme (upsert). Admin only."""
    svc = ChatbotService(db)
    return await svc.update_theme(org_id, chatbot_id, req, requester_id=current_user.id)


# ── Prechat Form ───────────────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/prechat-form",
            response_model=PrechatFormResponse)
async def get_prechat_form(
    org_id: UUID,
    chatbot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ChatbotService(db)
    return await svc.get_prechat_form(org_id, chatbot_id, requester_id=current_user.id)


@router.put("/organizations/{org_id}/chatbots/{chatbot_id}/prechat-form",
            response_model=PrechatFormResponse)
async def update_prechat_form(
    org_id: UUID,
    chatbot_id: UUID,
    req: PrechatFormUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update prechat lead capture form (upsert). Admin only."""
    svc = ChatbotService(db)
    return await svc.update_prechat_form(org_id, chatbot_id, req, requester_id=current_user.id)
