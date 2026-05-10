"""
Symmetric encryption for API keys stored in DB.
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography package.
Key is derived from settings.SECRET_KEY (must be ≥32 bytes).
"""

import base64
import hashlib
from typing import Optional

from app.config import get_settings

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        try:
            from cryptography.fernet import Fernet
            settings = get_settings()
            # Derive 32-byte Fernet key from SECRET_KEY
            raw = settings.SECRET_KEY.encode() if hasattr(settings, "SECRET_KEY") else settings.JWT_SECRET.encode()
            key_bytes = hashlib.sha256(raw).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            _fernet = Fernet(fernet_key)
        except ImportError:
            # cryptography not installed — fall back to base64 obfuscation only
            # (not secure — install cryptography package for production)
            _fernet = None
    return _fernet


def encrypt_api_key(plain: str) -> str:
    """Encrypt an API key for storage in DB."""
    f = _get_fernet()
    if f is None:
        # Fallback: base64 encode (NOT secure — install cryptography)
        return base64.b64encode(plain.encode()).decode()
    return f.encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> Optional[str]:
    """Decrypt an API key from DB storage."""
    if not encrypted:
        return None
    f = _get_fernet()
    if f is None:
        # Fallback: base64 decode
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            return None
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return None
