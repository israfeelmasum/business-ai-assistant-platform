"""
Language module — business logic.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.language.detector import (
    detect_language, is_rtl, get_language_info, SUPPORTED_LANGUAGES
)
from app.modules.language.schemas import (
    LanguageInfo, DetectLanguageRequest, DetectLanguageResponse,
    WidgetConfig, WidgetThemeConfig, WidgetPersonaConfig, WidgetPrechatConfig,
)
from app.modules.chatbots.repository import ChatbotRepository, PersonaRepository

logger = logging.getLogger(__name__)


class LanguageService:

    def __init__(self, db: AsyncSession):
        self.db         = db
        self.chatbots   = ChatbotRepository(db)
        self.personas   = PersonaRepository(db)

    def list_languages(self) -> List[LanguageInfo]:
        return [LanguageInfo(**lang) for lang in SUPPORTED_LANGUAGES]

    def detect(self, req: DetectLanguageRequest) -> DetectLanguageResponse:
        """
        Detect language from text.
        If chatbot_id is provided, we could constrain to supported languages
        in the future — for now, detect freely.
        """
        code = detect_language(req.text)
        rtl = is_rtl(code)

        # Simple confidence heuristic: longer texts → higher confidence
        text_len = len(req.text.strip())
        if text_len >= 20:
            confidence = "high"
        elif text_len >= 8:
            confidence = "medium"
        else:
            confidence = "low"

        return DetectLanguageResponse(
            detected=code, is_rtl=rtl, confidence=confidence
        )

    async def get_widget_config(self, chatbot_id: UUID) -> WidgetConfig:
        """
        Public endpoint — returns everything the widget needs to initialize.
        No auth required; only active chatbots are served.
        """
        from app.modules.chatbots.repository import ThemeRepository, PrechatFormRepository

        chatbot = await self.chatbots.get_by_id(chatbot_id)
        if not chatbot or not chatbot.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found or inactive",
            )

        persona = await self.personas.get_active(chatbot.id)

        # Always use repository for async-safe loading (avoid lazy relationship access)
        theme_repo = ThemeRepository(self.db)
        prechat_repo = PrechatFormRepository(self.db)
        theme = await theme_repo.get(chatbot.id)
        prechat = await prechat_repo.get(chatbot.id)

        default_lang = persona.default_language if persona else "en"
        supported_langs = (persona.supported_languages if persona else ["en"]) or ["en"]

        # Build theme config with defaults if theme is None
        if theme:
            theme_cfg = WidgetThemeConfig.model_validate(theme)
        else:
            theme_cfg = WidgetThemeConfig(
                color_primary="#2563EB", color_secondary="#7C3AED",
                color_accent="#06B6D4", color_background="#FFFFFF",
                color_text="#111827", color_user_bubble="#2563EB",
                color_bot_bubble="#F3F4F6", font_family="Inter",
                font_size_base=14, border_radius=12, widget_width=380,
                widget_height=600, position="bottom-right",
                dark_mode_enabled=False, dark_color_background="#1F2937",
                dark_color_text="#F9FAFB", custom_css=None,
                rtl_enabled=is_rtl(default_lang), template_name="modern",
            )

        persona_cfg = WidgetPersonaConfig(
            persona_name=persona.persona_name if persona else "Assistant",
            greeting_message=persona.greeting_message if persona else None,
            farewell_message=persona.farewell_message if persona else None,
            offline_message=persona.offline_message if persona else None,
            default_language=default_lang,
            supported_languages=supported_langs,
        )

        if prechat:
            prechat_cfg = WidgetPrechatConfig(
                is_enabled=prechat.is_enabled,
                title=prechat.title,
                message=prechat.message,
                fields=prechat.fields or [],
            )
        else:
            prechat_cfg = WidgetPrechatConfig(
                is_enabled=False, title=None, message=None, fields=[]
            )

        return WidgetConfig(
            chatbot_id=chatbot.id,
            chatbot_name=chatbot.name,
            avatar_url=chatbot.avatar_url,
            theme=theme_cfg,
            persona=persona_cfg,
            prechat=prechat_cfg,
            is_rtl=is_rtl(default_lang),
        )
