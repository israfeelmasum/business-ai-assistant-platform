"""
Language module — Pydantic schemas.
"""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LanguageInfo(BaseModel):
    code:   str
    name:   str     # English name
    native: str     # Name in the language itself
    rtl:    bool


class DetectLanguageRequest(BaseModel):
    text:           str
    chatbot_id:     Optional[UUID] = None   # If provided, constrain to chatbot's supported langs


class DetectLanguageResponse(BaseModel):
    detected:   str     # BCP-47 language code
    is_rtl:     bool
    confidence: str     # "high" | "medium" | "low"


# ── Widget Config ──────────────────────────────────────────────────────────────

class WidgetThemeConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    color_primary:          str
    color_secondary:        str
    color_accent:           str
    color_background:       str
    color_text:             str
    color_user_bubble:      str
    color_bot_bubble:       str
    font_family:            str
    font_size_base:         int
    border_radius:          int
    widget_width:           int
    widget_height:          int
    position:               str
    dark_mode_enabled:      bool
    dark_color_background:  str
    dark_color_text:        str
    custom_css:             Optional[str]
    rtl_enabled:            bool
    template_name:          str


class WidgetPersonaConfig(BaseModel):
    persona_name:       str
    greeting_message:   Optional[str]
    farewell_message:   Optional[str]
    offline_message:    Optional[str]
    default_language:   str
    supported_languages: List[str]


class WidgetPrechatConfig(BaseModel):
    is_enabled: bool
    title:      Optional[str]
    message:    Optional[str]
    fields:     List[dict]


class WidgetConfig(BaseModel):
    """
    Single API call response for widget initialization.
    Widget fetches this on page load to configure itself.
    """
    chatbot_id:     UUID
    chatbot_name:   str
    avatar_url:     Optional[str]
    theme:          WidgetThemeConfig
    persona:        WidgetPersonaConfig
    prechat:        WidgetPrechatConfig
    is_rtl:         bool    # convenience: True if default_language is RTL
