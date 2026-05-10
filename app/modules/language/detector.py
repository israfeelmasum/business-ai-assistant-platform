"""
Language detection — lightweight, zero external dependencies.

Uses Unicode block analysis to identify scripts, then infers language.
Covers Fellow BOT's primary markets: Bangladesh (Bangla), Arabic-speaking
countries, South/Southeast Asia, and Latin-script languages.

Falls back to "en" (English) when detection is ambiguous.
"""

from __future__ import annotations
import re
from typing import Optional

# ── RTL Languages ──────────────────────────────────────────────────────────────

RTL_LANGUAGES: set[str] = {
    "ar",   # Arabic
    "he",   # Hebrew
    "fa",   # Persian / Farsi
    "ur",   # Urdu
    "ku",   # Kurdish
    "yi",   # Yiddish
    "ps",   # Pashto
    "sd",   # Sindhi
    "dv",   # Dhivehi (Maldivian)
}

# ── Supported Languages Registry ──────────────────────────────────────────────

SUPPORTED_LANGUAGES: list[dict] = [
    # Code, English name, Native name, RTL
    {"code": "en", "name": "English",    "native": "English",       "rtl": False},
    {"code": "bn", "name": "Bengali",    "native": "বাংলা",          "rtl": False},
    {"code": "ar", "name": "Arabic",     "native": "العربية",        "rtl": True},
    {"code": "hi", "name": "Hindi",      "native": "हिन्दी",          "rtl": False},
    {"code": "ur", "name": "Urdu",       "native": "اردو",           "rtl": True},
    {"code": "fa", "name": "Persian",    "native": "فارسی",          "rtl": True},
    {"code": "he", "name": "Hebrew",     "native": "עברית",          "rtl": True},
    {"code": "zh", "name": "Chinese",    "native": "中文",            "rtl": False},
    {"code": "ja", "name": "Japanese",   "native": "日本語",           "rtl": False},
    {"code": "ko", "name": "Korean",     "native": "한국어",           "rtl": False},
    {"code": "fr", "name": "French",     "native": "Français",       "rtl": False},
    {"code": "de", "name": "German",     "native": "Deutsch",        "rtl": False},
    {"code": "es", "name": "Spanish",    "native": "Español",        "rtl": False},
    {"code": "pt", "name": "Portuguese", "native": "Português",      "rtl": False},
    {"code": "ru", "name": "Russian",    "native": "Русский",        "rtl": False},
    {"code": "tr", "name": "Turkish",    "native": "Türkçe",         "rtl": False},
    {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt",     "rtl": False},
    {"code": "id", "name": "Indonesian", "native": "Bahasa Indonesia","rtl": False},
    {"code": "ms", "name": "Malay",      "native": "Bahasa Melayu",  "rtl": False},
    {"code": "th", "name": "Thai",       "native": "ภาษาไทย",          "rtl": False},
    {"code": "ta", "name": "Tamil",      "native": "தமிழ்",           "rtl": False},
    {"code": "te", "name": "Telugu",     "native": "తెలుగు",           "rtl": False},
    {"code": "ml", "name": "Malayalam",  "native": "മലയാളം",           "rtl": False},
    {"code": "pa", "name": "Punjabi",    "native": "ਪੰਜਾਬੀ",           "rtl": False},
    {"code": "gu", "name": "Gujarati",   "native": "ગુજરાતી",          "rtl": False},
    {"code": "mr", "name": "Marathi",    "native": "मराठी",            "rtl": False},
    {"code": "ne", "name": "Nepali",     "native": "नेपाली",           "rtl": False},
    {"code": "si", "name": "Sinhala",    "native": "සිංහල",            "rtl": False},
]

_LANG_MAP = {lang["code"]: lang for lang in SUPPORTED_LANGUAGES}


# ── Unicode Block Ranges ───────────────────────────────────────────────────────

_SCRIPT_RANGES = [
    # (start, end, language_code)
    (0x0980, 0x09FF, "bn"),   # Bengali / Bangla
    (0x0600, 0x06FF, "ar"),   # Arabic — could be ar/ur/fa; refined below
    (0x0750, 0x077F, "ar"),   # Arabic Supplement
    (0xFB50, 0xFDFF, "ar"),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF, "ar"),   # Arabic Presentation Forms-B
    (0x0900, 0x097F, "hi"),   # Devanagari (Hindi, Marathi, Nepali)
    (0x0400, 0x04FF, "ru"),   # Cyrillic
    (0x0E00, 0x0E7F, "th"),   # Thai
    (0x4E00, 0x9FFF, "zh"),   # CJK Unified Ideographs
    (0x3040, 0x309F, "ja"),   # Hiragana
    (0x30A0, 0x30FF, "ja"),   # Katakana
    (0xAC00, 0xD7AF, "ko"),   # Hangul Syllables
    (0x0590, 0x05FF, "he"),   # Hebrew
    (0x0A00, 0x0A7F, "pa"),   # Gurmukhi (Punjabi)
    (0x0A80, 0x0AFF, "gu"),   # Gujarati
    (0x0B00, 0x0B7F, "or"),   # Oriya
    (0x0B80, 0x0BFF, "ta"),   # Tamil
    (0x0C00, 0x0C7F, "te"),   # Telugu
    (0x0C80, 0x0CFF, "kn"),   # Kannada
    (0x0D00, 0x0D7F, "ml"),   # Malayalam
    (0x0D80, 0x0DFF, "si"),   # Sinhala
    (0x0600, 0x06FF, "ur"),   # Urdu (overlaps Arabic — resolved by context)
]


def detect_language(text: str) -> str:
    """
    Detect the primary language of `text`.
    Returns a BCP-47 language code (e.g. "en", "bn", "ar").
    Falls back to "en" on ambiguity or very short text.
    """
    if not text or len(text.strip()) < 3:
        return "en"

    counts: dict[str, int] = {}
    for char in text:
        cp = ord(char)
        for start, end, lang in _SCRIPT_RANGES:
            if start <= cp <= end:
                # Urdu vs Arabic disambiguation: Urdu has specific characters
                if lang == "ar" and _is_likely_urdu(char):
                    lang = "ur"
                # Devanagari: check for Marathi/Nepali patterns vs Hindi — default hi
                counts[lang] = counts.get(lang, 0) + 1
                break

    if not counts:
        return "en"  # all Latin / ASCII → assume English

    # Dominant script wins
    dominant = max(counts, key=counts.__getitem__)
    dominant_ratio = counts[dominant] / sum(counts.values())

    # Only report if dominant script is > 40% of non-space characters
    non_space = sum(1 for c in text if not c.isspace())
    script_chars = sum(counts.values())
    if non_space > 0 and script_chars / non_space < 0.3:
        return "en"  # mostly Latin with some foreign chars

    return dominant


def is_rtl(language_code: str) -> bool:
    """Return True if language is written right-to-left."""
    return language_code.lower() in RTL_LANGUAGES


def get_language_info(code: str) -> Optional[dict]:
    """Return full language metadata for a given code, or None."""
    return _LANG_MAP.get(code.lower())


# ── Internal helpers ───────────────────────────────────────────────────────────

_URDU_SPECIFIC = {
    '\u06BE',  # ہ (heh doachashmee — Urdu-specific)
    '\u06C1',  # ہ (heh goal)
    '\u06CC',  # ی (Urdu ye)
    '\u06BA',  # ں (noon ghunna)
    '\u06C3',  # ة with two dots above
}


def _is_likely_urdu(char: str) -> bool:
    return char in _URDU_SPECIFIC
