"""
Schemas for chat and conversation endpoints.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class UserInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session ID from client app")
    message: str = Field(..., min_length=1, max_length=2000)
    user_info: UserInfo = Field(default_factory=UserInfo)
    entity_type: str | None = Field(None, description="Selected entity type filter")
    image_base64: str | None = Field(None, description="Base64 encoded image string for vision processing")
    stream: bool = Field(False, description="Enable streaming response")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Chat history for context")


class ChatResponse(BaseModel):
    session_id: str
    message: str
    entity_types: list[str] | None = None
    conversation_id: uuid.UUID


class ConversationResponse(BaseModel):
    id: uuid.UUID
    session_id: str
    user_phone: str | None = None
    user_info: dict
    messages: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
