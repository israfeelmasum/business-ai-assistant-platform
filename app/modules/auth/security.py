"""
Auth security — password hashing, JWT creation/verification.
Uses HS256 for simplicity (swap to RS256 with key files for production).
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ─── JWT Config ────────────────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES  = 60          # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS    = 30          # 30 days
ALGORITHM                    = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: UUID, role: str, email: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, hashed_token). Store hash in DB, send raw to client."""
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_access_token(token: str) -> dict:
    """Decode and validate JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token")


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_key(prefix: str = "fb") -> tuple[str, str, str]:
    """Returns (raw_key, key_prefix, key_hash). Store hash in DB."""
    raw = f"{prefix}_{secrets.token_urlsafe(48)}"
    key_prefix = raw[:10]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_prefix, key_hash
