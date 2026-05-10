"""
Schemas for AI Provider endpoints.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class AIProviderCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["Ollama Llama 3.1"])
    model_name: str = Field(..., max_length=100, examples=["llama3.1"])
    provider_type: str = Field(..., max_length=50, examples=["ollama"])
    config: dict = Field(default_factory=dict)


class AIProviderUpdate(BaseModel):
    name: str | None = None
    model_name: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class AIProviderResponse(BaseModel):
    id: uuid.UUID
    name: str
    model_name: str
    provider_type: str
    config: dict
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
