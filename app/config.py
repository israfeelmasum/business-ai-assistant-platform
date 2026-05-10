"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_chatbot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Provider Keys
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # App
    APP_NAME: str = "AI Chatbot Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Embedding config
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Chat config
    MAX_CONTEXT_RESULTS: int = 5
    MAX_CONVERSATION_MESSAGES: int = 100

    # CORS — comma-separated origins in .env
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:4000,http://127.0.0.1:4000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:9000,http://127.0.0.1:9000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # JWT
    JWT_SECRET: str = "change-this-to-a-strong-random-secret-in-production"

    # Email (SMTP) — set credentials in .env, never hardcode
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_SERVER: str = "smtp.gmail.com"   # alias kept for back-compat
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    AUTHORITY_EMAIL: str = ""
    ADMIN_EMAIL: str = ""

    # API Key (legacy webhook auth)
    API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
