"""
Schemas for Client registration and management.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class ClientRegister(BaseModel):
    name: str = Field(..., max_length=255, examples=["ICT Bangladesh LMS"])
    provider_id: uuid.UUID | None = Field(None, description="Chosen AI provider ID")
    config: dict = Field(default_factory=dict)
    welcome_message: str | None = Field("Hello! How can I help you today?")

class ClientUpdate(BaseModel):
    name: str | None = None
    provider_id: uuid.UUID | None = None
    config: dict | None = None
    welcome_message: str | None = None
    
    # 👇 মডার্ন সিনট্যাক্সে অ্যাড করা হলো
    logo_base64: str | None = None
    
    is_active: bool | None = None

class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str
    provider_id: uuid.UUID | None
    config: dict
    welcome_message: str | None
    
    # 👇 মডার্ন সিনট্যাক্সে অ্যাড করা হলো
    logo_base64: str | None = None
    
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class ClientRegisteredResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str
    api_secret: str
    message: str = "Store your api_secret safely. It will not be shown again."

    model_config = {"from_attributes": True}
    
