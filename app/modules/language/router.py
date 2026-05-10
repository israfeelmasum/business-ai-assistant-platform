"""
Language module — router.

Public endpoints (no auth required):
  GET  /languages              — list all supported languages
  POST /detect-language        — detect language from text
  GET  /widget/config          — full widget initialization config (theme + persona + prechat)
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.language.schemas import (
    LanguageInfo, DetectLanguageRequest, DetectLanguageResponse, WidgetConfig,
)
from app.modules.language.service import LanguageService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Language & Widget Config"])


@router.get("/languages", response_model=List[LanguageInfo])
async def list_languages(
    db: AsyncSession = Depends(get_db),
):
    """
    List all supported languages with their RTL flags.
    Used by admin dashboard language pickers and widget locale selectors.
    Public — no auth required.
    """
    svc = LanguageService(db)
    return svc.list_languages()


@router.post("/detect-language", response_model=DetectLanguageResponse)
async def detect_language(
    req: DetectLanguageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Detect the language of a given text string.
    Returns a BCP-47 language code, RTL flag, and confidence level.
    Public — no auth required.
    """
    svc = LanguageService(db)
    return svc.detect(req)


@router.get("/widget/config", response_model=WidgetConfig)
async def get_widget_config(
    chatbot_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Widget initialization endpoint. Called once on page load.

    Returns everything the embeddable widget needs:
    - Theme (colors, fonts, layout, RTL flag)
    - Persona (bot name, greeting, supported languages)
    - Pre-chat form (fields, enabled flag)

    Public — no auth required. Validates chatbot is active before responding.
    """
    svc = LanguageService(db)
    return await svc.get_widget_config(chatbot_id)
