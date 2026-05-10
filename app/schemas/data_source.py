"""
Schemas for data source configuration and sync operations.
"""

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class PaginationType(str, Enum):
    NONE = "none"
    OFFSET_LIMIT = "offset_limit"
    PAGE_NUMBER = "page_number"
    CURSOR = "cursor"


class DataSourceCreate(BaseModel):
    name: str = Field(..., max_length=255, examples=["Product Catalog"])
    entity_type: str = Field(..., max_length=100, examples=["course"])
    api_url: str = Field(..., examples=["https://mystore.com/api/products"])
    auth_type: AuthType = Field(default=AuthType.NONE)
    auth_config: dict = Field(default_factory=dict, examples=[{"token": "your-bearer-token"}])
    request_headers: dict = Field(default_factory=dict)
    pagination_type: PaginationType = Field(default=PaginationType.NONE)
    pagination_config: dict = Field(default_factory=dict, examples=[{"limit_param": "limit", "offset_param": "offset", "page_size": 50}])
    data_path: str = Field(default="", examples=["items", "data.results"])
    id_field: str = Field(default="id", examples=["id", "product_id"])
    field_mapping: dict = Field(default_factory=dict, examples=[{"product_name": "title", "product_price": "price"}])
    sync_interval_minutes: int = Field(default=30, ge=5, le=1440)


class DataSourceUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    api_url: str | None = None
    auth_type: AuthType | None = None
    auth_config: dict | None = None
    request_headers: dict | None = None
    pagination_type: PaginationType | None = None
    pagination_config: dict | None = None
    data_path: str | None = None
    id_field: str | None = None
    field_mapping: dict | None = None
    sync_interval_minutes: int | None = Field(None, ge=5, le=1440)
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    name: str
    entity_type: str
    api_url: str
    auth_type: str
    pagination_type: str
    data_path: str
    id_field: str
    field_mapping: dict
    sync_interval_minutes: int
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncLogResponse(BaseModel):
    id: uuid.UUID
    data_source_id: uuid.UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    total_fetched: int
    created_count: int
    updated_count: int
    skipped_count: int
    deleted_count: int
    error_count: int
    errors: list

    model_config = {"from_attributes": True}


class ManualSyncResponse(BaseModel):
    success: bool
    message: str
    sync_log_id: uuid.UUID


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    record_count: int
    sample_records: list[dict]
    sample_fields: list[str]
