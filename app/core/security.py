"""
API key generation and hashing utilities.
"""

import secrets
import hashlib


def generate_api_key(prefix: str = "acb") -> str:
    """Generate a unique API key. Example: acb_a1b2c3d4e5f6..."""
    random_part = secrets.token_hex(24)
    return f"{prefix}_{random_part}"


def generate_api_secret() -> str:
    """Generate a secure API secret."""
    return secrets.token_hex(32)


def hash_secret(secret: str) -> str:
    """Hash the API secret for storage."""
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Verify a plain secret against its hash."""
    return hash_secret(plain_secret) == hashed_secret
