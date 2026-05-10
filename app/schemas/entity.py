"""
Schemas for entity sync operations (create/update/delete).
"""

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SyncAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class EntitySyncRequest(BaseModel):
    entity_type: str = Field(..., max_length=100, examples=["course"])
    action: SyncAction = Field(..., examples=["create"])
    entity_id: str = Field(..., max_length=255, examples=["course-abc-123"])
    data: dict = Field(default_factory=dict)


class EntitySyncResponse(BaseModel):
    success: bool
    message: str
    entity_id: str
    entity_type: str
    action: SyncAction


class EntityTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str | None
    description: str | None
    icon: str | None

    model_config = {"from_attributes": True}


class BulkEntitySyncRequest(BaseModel):
    entities: list[EntitySyncRequest] = Field(..., min_length=1, max_length=100)


class BulkEntitySyncResponse(BaseModel):
    success: bool
    total: int
    succeeded: int
    failed: int
    results: list[EntitySyncResponse]
