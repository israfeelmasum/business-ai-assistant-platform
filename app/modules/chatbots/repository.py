"""
Chatbots module — repository layer.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.chatbots.models import (
    Chatbot, ChatbotModelConfig, ChatbotPersona, ChatbotPrompt,
    ChatbotGuardrail, ChatbotDeployment, ChatbotTheme, ChatbotPrechatForm,
    PromptLayer
)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:100]


class ChatbotRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def unique_slug(self, org_id: UUID, base: str) -> str:
        slug = base
        counter = 1
        while True:
            result = await self.db.execute(
                select(Chatbot).where(Chatbot.org_id == org_id, Chatbot.slug == slug)
            )
            if not result.scalar_one_or_none():
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def create(
        self, org_id: UUID, name: str, slug: str, created_by: UUID,
        description: Optional[str] = None, avatar_url: Optional[str] = None,
    ) -> Chatbot:
        bot = Chatbot(
            org_id=org_id, name=name, slug=slug, created_by=created_by,
            description=description, avatar_url=avatar_url,
        )
        self.db.add(bot)
        await self.db.flush()

        # Auto-create theme and prechat form stubs
        self.db.add(ChatbotTheme(chatbot_id=bot.id))
        self.db.add(ChatbotPrechatForm(chatbot_id=bot.id))
        await self.db.flush()
        return bot

    async def get_by_id(self, chatbot_id: UUID, org_id: Optional[UUID] = None) -> Optional[Chatbot]:
        q = select(Chatbot).options(selectinload(Chatbot.theme)).where(Chatbot.id == chatbot_id)
        if org_id:
            q = q.where(Chatbot.org_id == org_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_slug(self, org_id: UUID, slug: str) -> Optional[Chatbot]:
        result = await self.db.execute(
            select(Chatbot).where(Chatbot.org_id == org_id, Chatbot.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_org_chatbots(self, org_id: UUID, include_inactive: bool = False) -> List[Chatbot]:
        q = select(Chatbot).where(Chatbot.org_id == org_id)
        if not include_inactive:
            q = q.where(Chatbot.is_active == True)
        q = q.order_by(Chatbot.name)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(self, chatbot_id: UUID, org_id: UUID, **kwargs) -> Optional[Chatbot]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(Chatbot)
            .where(Chatbot.id == chatbot_id, Chatbot.org_id == org_id)
            .values(**kwargs)
        )
        return await self.get_by_id(chatbot_id, org_id)

    async def delete(self, chatbot_id: UUID, org_id: UUID) -> None:
        await self.db.execute(
            delete(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.org_id == org_id)
        )


class ModelConfigRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_for_task(self, chatbot_id: UUID, task: str) -> Optional[ChatbotModelConfig]:
        result = await self.db.execute(
            select(ChatbotModelConfig).where(
                ChatbotModelConfig.chatbot_id == chatbot_id,
                ChatbotModelConfig.task == task,
                ChatbotModelConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_chatbot(self, chatbot_id: UUID) -> List[ChatbotModelConfig]:
        result = await self.db.execute(
            select(ChatbotModelConfig).where(ChatbotModelConfig.chatbot_id == chatbot_id)
        )
        return list(result.scalars().all())

    async def upsert(self, chatbot_id: UUID, task: str, **kwargs) -> ChatbotModelConfig:
        existing = await self.get_for_task(chatbot_id, task)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self.db.flush()
            return existing
        cfg = ChatbotModelConfig(chatbot_id=chatbot_id, task=task, **kwargs)
        self.db.add(cfg)
        await self.db.flush()
        return cfg


class PersonaRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self, chatbot_id: UUID) -> Optional[ChatbotPersona]:
        result = await self.db.execute(
            select(ChatbotPersona).where(
                ChatbotPersona.chatbot_id == chatbot_id,
                ChatbotPersona.is_active == True,
            ).order_by(ChatbotPersona.version.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, chatbot_id: UUID, **kwargs) -> ChatbotPersona:
        persona = ChatbotPersona(chatbot_id=chatbot_id, **kwargs)
        self.db.add(persona)
        await self.db.flush()
        return persona

    async def update(self, persona_id: UUID, chatbot_id: UUID, **kwargs) -> Optional[ChatbotPersona]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(ChatbotPersona)
            .where(ChatbotPersona.id == persona_id, ChatbotPersona.chatbot_id == chatbot_id)
            .values(**kwargs)
        )
        result = await self.db.execute(
            select(ChatbotPersona).where(ChatbotPersona.id == persona_id)
        )
        return result.scalar_one_or_none()


class PromptRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_chatbot_prompts(
        self, chatbot_id: UUID, layer: Optional[PromptLayer] = None,
        active_only: bool = True
    ) -> List[ChatbotPrompt]:
        q = select(ChatbotPrompt).where(ChatbotPrompt.chatbot_id == chatbot_id)
        if layer:
            q = q.where(ChatbotPrompt.layer == layer)
        if active_only:
            q = q.where(ChatbotPrompt.is_active == True)
        q = q.order_by(ChatbotPrompt.layer, ChatbotPrompt.created_at)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, prompt_id: UUID, chatbot_id: UUID) -> Optional[ChatbotPrompt]:
        result = await self.db.execute(
            select(ChatbotPrompt).where(
                ChatbotPrompt.id == prompt_id,
                ChatbotPrompt.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, chatbot_id: UUID, created_by: UUID, **kwargs) -> ChatbotPrompt:
        p = ChatbotPrompt(chatbot_id=chatbot_id, created_by=created_by, **kwargs)
        self.db.add(p)
        await self.db.flush()
        return p

    async def update(self, prompt_id: UUID, chatbot_id: UUID, **kwargs) -> Optional[ChatbotPrompt]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        # Bump version on content change
        if "content" in kwargs:
            current = await self.get_by_id(prompt_id, chatbot_id)
            if current:
                kwargs["version"] = current.version + 1
        await self.db.execute(
            update(ChatbotPrompt)
            .where(ChatbotPrompt.id == prompt_id, ChatbotPrompt.chatbot_id == chatbot_id)
            .values(**kwargs)
        )
        return await self.get_by_id(prompt_id, chatbot_id)

    async def delete(self, prompt_id: UUID, chatbot_id: UUID) -> None:
        await self.db.execute(
            delete(ChatbotPrompt).where(
                ChatbotPrompt.id == prompt_id,
                ChatbotPrompt.chatbot_id == chatbot_id,
            )
        )


class GuardrailRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_chatbot(self, chatbot_id: UUID, active_only: bool = True) -> List[ChatbotGuardrail]:
        q = select(ChatbotGuardrail).where(ChatbotGuardrail.chatbot_id == chatbot_id)
        if active_only:
            q = q.where(ChatbotGuardrail.is_active == True)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, rule_id: UUID, chatbot_id: UUID) -> Optional[ChatbotGuardrail]:
        result = await self.db.execute(
            select(ChatbotGuardrail).where(
                ChatbotGuardrail.id == rule_id,
                ChatbotGuardrail.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, chatbot_id: UUID, **kwargs) -> ChatbotGuardrail:
        g = ChatbotGuardrail(chatbot_id=chatbot_id, **kwargs)
        self.db.add(g)
        await self.db.flush()
        return g

    async def update(self, rule_id: UUID, chatbot_id: UUID, **kwargs) -> Optional[ChatbotGuardrail]:
        await self.db.execute(
            update(ChatbotGuardrail)
            .where(ChatbotGuardrail.id == rule_id, ChatbotGuardrail.chatbot_id == chatbot_id)
            .values(**kwargs)
        )
        return await self.get_by_id(rule_id, chatbot_id)

    async def delete(self, rule_id: UUID, chatbot_id: UUID) -> None:
        await self.db.execute(
            delete(ChatbotGuardrail).where(
                ChatbotGuardrail.id == rule_id,
                ChatbotGuardrail.chatbot_id == chatbot_id,
            )
        )


class DeploymentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_chatbot(self, chatbot_id: UUID) -> List[ChatbotDeployment]:
        result = await self.db.execute(
            select(ChatbotDeployment).where(ChatbotDeployment.chatbot_id == chatbot_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, dep_id: UUID, chatbot_id: UUID) -> Optional[ChatbotDeployment]:
        result = await self.db.execute(
            select(ChatbotDeployment).where(
                ChatbotDeployment.id == dep_id,
                ChatbotDeployment.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, chatbot_id: UUID, **kwargs) -> ChatbotDeployment:
        d = ChatbotDeployment(chatbot_id=chatbot_id, **kwargs)
        self.db.add(d)
        await self.db.flush()
        return d

    async def update(self, dep_id: UUID, chatbot_id: UUID, **kwargs) -> Optional[ChatbotDeployment]:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(ChatbotDeployment)
            .where(ChatbotDeployment.id == dep_id, ChatbotDeployment.chatbot_id == chatbot_id)
            .values(**kwargs)
        )
        return await self.get_by_id(dep_id, chatbot_id)


class ThemeRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, chatbot_id: UUID) -> Optional[ChatbotTheme]:
        result = await self.db.execute(
            select(ChatbotTheme).where(ChatbotTheme.chatbot_id == chatbot_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, chatbot_id: UUID, **kwargs) -> ChatbotTheme:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        existing = await self.get(chatbot_id)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self.db.flush()
            return existing
        t = ChatbotTheme(chatbot_id=chatbot_id, **kwargs)
        self.db.add(t)
        await self.db.flush()
        return t


class PrechatFormRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, chatbot_id: UUID) -> Optional[ChatbotPrechatForm]:
        result = await self.db.execute(
            select(ChatbotPrechatForm).where(ChatbotPrechatForm.chatbot_id == chatbot_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, chatbot_id: UUID, **kwargs) -> ChatbotPrechatForm:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        existing = await self.get(chatbot_id)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self.db.flush()
            return existing
        f = ChatbotPrechatForm(chatbot_id=chatbot_id, **kwargs)
        self.db.add(f)
        await self.db.flush()
        return f
