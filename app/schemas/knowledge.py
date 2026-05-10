"""Schemas for AI Knowledge entries."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class KnowledgeResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    entity_type_id: uuid.UUID
    summary: str
    meta_data: dict = Field(default_factory=dict, alias="metadata") # Alias maps to JSON response
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}