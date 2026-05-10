"""
Auto-Sync Service - The core engine that pulls data from external APIs,
maps fields, detects changes via hashing, and syncs to the knowledge base.
"""

import json
import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.data_source import DataSource
from app.models.sync_log import SyncLog
from app.models.ai_entity import AIEntity
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.sync_log_repository import SyncLogRepository
from app.repositories.entity_type_repository import EntityTypeRepository
from app.repositories.ai_entity_repository import AIEntityRepository
from app.repositories.ai_knowledge_repository import AIKnowledgeRepository
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

MAX_RECORDS_PER_SYNC = 10000
HTTP_TIMEOUT = 30
STALE_SYNC_MINUTES = 30


class AutoSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ds_repo = DataSourceRepository(db)
        self.log_repo = SyncLogRepository(db)
        self.type_repo = EntityTypeRepository(db)
        self.entity_repo = AIEntityRepository(db)
        self.knowledge_repo = AIKnowledgeRepository(db)
        self.knowledge_service = KnowledgeService(db)

    async def execute_sync(self, data_source: DataSource) -> SyncLog:
        """Execute a full sync for a data source."""
        # Check for stale running sync
        latest_log = await self.log_repo.get_latest_by_source(data_source.id)
        if latest_log and latest_log.status == "running":
            elapsed = datetime.now(timezone.utc) - latest_log.started_at
            if elapsed < timedelta(minutes=STALE_SYNC_MINUTES):
                logger.info(f"Sync already running for {data_source.name}, skipping")
                return latest_log
            # Mark stale sync as failed
            await self.log_repo.update_log(latest_log.id, status="failed", finished_at=datetime.now(timezone.utc))

        # Create new sync log
        sync_log = SyncLog(
            data_source_id=data_source.id,
            client_id=data_source.client_id,
            status="running",
        )
        sync_log = await self.log_repo.create(sync_log)
        await self.db.commit()

        counts = {
            "total_fetched": 0, "created_count": 0, "updated_count": 0,
            "skipped_count": 0, "deleted_count": 0, "error_count": 0,
        }
        errors = []

        try:
            # 1. Fetch all records from external API
            records = await self._fetch_all_records(data_source)
            counts["total_fetched"] = len(records)

            # 2. Get or create entity type
            entity_type = await self.type_repo.get_or_create(
                data_source.client_id, data_source.entity_type
            )

            # 3. Process each record
            fetched_external_ids = set()
            for record in records:
                try:
                    external_id = self._extract_from_path(record, data_source.id_field)
                    if external_id is None:
                        errors.append({"external_id": "unknown", "error": f"Missing id_field: {data_source.id_field}"})
                        counts["error_count"] += 1
                        continue

                    external_id = str(external_id)
                    fetched_external_ids.add(external_id)

                    # Apply field mapping
                    mapped_data = self._apply_field_mapping(record, data_source.field_mapping)

                    # Compute hash for change detection
                    data_hash = self._compute_hash(mapped_data)

                    # Check existing entity
                    existing = await self.entity_repo.get_by_external_id(
                        data_source.client_id, entity_type.id, external_id
                    )

                    if existing and existing.data_hash == data_hash:
                        counts["skipped_count"] += 1
                        continue

                    if existing:
                        # Update
                        await self.entity_repo.update_data(existing.id, mapped_data)
                        await self.db.execute(
                            update(AIEntity).where(AIEntity.id == existing.id).values(data_hash=data_hash)
                        )
                        await self.knowledge_service.update_knowledge(
                            entity_id=existing.id,
                            entity_type_name=entity_type.name,
                            data=mapped_data,
                        )
                        counts["updated_count"] += 1
                    else:
                        # Create
                        entity = AIEntity(
                            client_id=data_source.client_id,
                            entity_type_id=entity_type.id,
                            external_id=external_id,
                            data=mapped_data,
                            data_hash=data_hash,
                        )
                        created = await self.entity_repo.create(entity)
                        await self.knowledge_service.generate_knowledge(
                            client_id=data_source.client_id,
                            entity_id=created.id,
                            entity_type_id=entity_type.id,
                            entity_type_name=entity_type.name,
                            data=mapped_data,
                        )
                        counts["created_count"] += 1

                except Exception as e:
                    ext_id = str(external_id) if 'external_id' in dir() else "unknown"
                    errors.append({"external_id": ext_id, "error": str(e)})
                    counts["error_count"] += 1
                    logger.error(f"Error processing record: {e}")

            # 4. Detect deletions - entities that exist in DB but not in fetched data
            deleted_count = await self._detect_deletions(
                data_source.client_id, entity_type.id, fetched_external_ids
            )
            counts["deleted_count"] = deleted_count

            # 5. Determine final status
            if counts["error_count"] == 0:
                status = "success"
            elif counts["error_count"] < counts["total_fetched"]:
                status = "partial"
            else:
                status = "failed"

        except Exception as e:
            status = "failed"
            errors.append({"external_id": "system", "error": str(e)})
            counts["error_count"] += 1
            logger.error(f"Sync failed for {data_source.name}: {e}")

        # 6. Update sync log and data source
        await self.log_repo.update_log(
            sync_log.id,
            status=status,
            finished_at=datetime.now(timezone.utc),
            errors=errors,
            **counts,
        )
        await self.ds_repo.update_last_synced(data_source.id)
        await self.db.commit()

        # Reload the sync log to return updated version
        updated_log = await self.log_repo.get_latest_by_source(data_source.id)
        logger.info(
            f"Sync completed for {data_source.name}: "
            f"fetched={counts['total_fetched']}, created={counts['created_count']}, "
            f"updated={counts['updated_count']}, skipped={counts['skipped_count']}, "
            f"deleted={counts['deleted_count']}, errors={counts['error_count']}"
        )
        return updated_log or sync_log

    async def test_connection(self, data_source: DataSource) -> dict:
        """Test connection to external API without syncing. Returns sample data."""
        try:
            client = self._build_http_client(data_source)
            async with client:
                response = await client.get(data_source.api_url)
                response.raise_for_status()
                data = response.json()

            records = self._extract_array(data, data_source.data_path)
            sample = records[:3] if len(records) > 3 else records

            # Apply field mapping to sample
            mapped_sample = [self._apply_field_mapping(r, data_source.field_mapping) for r in sample]

            # Collect all field names from sample
            fields = set()
            for r in sample:
                fields.update(r.keys())

            return {
                "success": True,
                "message": f"Connected successfully. Found {len(records)} records.",
                "record_count": len(records),
                "sample_records": mapped_sample,
                "sample_fields": sorted(fields),
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                "record_count": 0,
                "sample_records": [],
                "sample_fields": [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "record_count": 0,
                "sample_records": [],
                "sample_fields": [],
            }

    # ─── Internal Methods ──────────────────────────────────────────────

    async def _fetch_all_records(self, data_source: DataSource) -> list[dict]:
        """Fetch all records from external API, handling pagination."""
        client = self._build_http_client(data_source)
        all_records = []

        async with client:
            if data_source.pagination_type == "none":
                response = await client.get(data_source.api_url)
                response.raise_for_status()
                data = response.json()
                all_records = self._extract_array(data, data_source.data_path)

            elif data_source.pagination_type == "offset_limit":
                config = data_source.pagination_config
                limit_param = config.get("limit_param", "limit")
                offset_param = config.get("offset_param", "offset")
                page_size = config.get("page_size", 50)
                offset = 0

                while len(all_records) < MAX_RECORDS_PER_SYNC:
                    params = {limit_param: page_size, offset_param: offset}
                    response = await client.get(data_source.api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    records = self._extract_array(data, data_source.data_path)
                    if not records:
                        break
                    all_records.extend(records)
                    if len(records) < page_size:
                        break
                    offset += page_size

            elif data_source.pagination_type == "page_number":
                config = data_source.pagination_config
                page_param = config.get("page_param", "page")
                page_size_param = config.get("page_size_param", "per_page")
                page_size = config.get("page_size", 25)
                page = 1

                while len(all_records) < MAX_RECORDS_PER_SYNC:
                    params = {page_param: page, page_size_param: page_size}
                    response = await client.get(data_source.api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    records = self._extract_array(data, data_source.data_path)
                    if not records:
                        break
                    all_records.extend(records)
                    if len(records) < page_size:
                        break
                    page += 1

            elif data_source.pagination_type == "cursor":
                config = data_source.pagination_config
                cursor_param = config.get("cursor_param", "cursor")
                cursor_path = config.get("cursor_path", "meta.next_cursor")
                cursor = None

                while len(all_records) < MAX_RECORDS_PER_SYNC:
                    params = {}
                    if cursor:
                        params[cursor_param] = cursor
                    response = await client.get(data_source.api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    records = self._extract_array(data, data_source.data_path)
                    if not records:
                        break
                    all_records.extend(records)
                    cursor = self._extract_from_path(data, cursor_path)
                    if not cursor:
                        break

        return all_records[:MAX_RECORDS_PER_SYNC]

    def _build_http_client(self, data_source: DataSource) -> httpx.AsyncClient:
        """Build HTTP client with appropriate authentication."""
        headers = dict(data_source.request_headers or {})
        headers.setdefault("Accept", "application/json")
        auth = None

        if data_source.auth_type == "bearer":
            token = data_source.auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif data_source.auth_type == "api_key":
            header_name = data_source.auth_config.get("header", "X-API-Key")
            header_value = data_source.auth_config.get("value", "")
            headers[header_name] = header_value
        elif data_source.auth_type == "basic":
            username = data_source.auth_config.get("username", "")
            password = data_source.auth_config.get("password", "")
            auth = httpx.BasicAuth(username, password)

        return httpx.AsyncClient(
            headers=headers,
            auth=auth,
            timeout=httpx.Timeout(HTTP_TIMEOUT),
            follow_redirects=True,
        )

    def _extract_array(self, data: any, data_path: str) -> list[dict]:
        """Extract array of records from API response using data_path."""
        if not data_path:
            if isinstance(data, list):
                return data
            return [data] if isinstance(data, dict) else []

        result = self._extract_from_path(data, data_path)
        if isinstance(result, list):
            return result
        return [result] if isinstance(result, dict) else []

    @staticmethod
    def _extract_from_path(data: any, path: str) -> any:
        """Navigate nested dicts/lists with dot-separated path."""
        if not path:
            return data
        current = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _apply_field_mapping(record: dict, field_mapping: dict) -> dict:
        """Apply field mapping to rename fields. If mapping is empty, pass through."""
        if not field_mapping:
            return dict(record)

        mapped = {}
        for source_field, target_field in field_mapping.items():
            # Support dot notation for nested source fields
            if "." in source_field:
                parts = source_field.split(".")
                value = record
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
            else:
                value = record.get(source_field)
            mapped[target_field] = value
        return mapped

    @staticmethod
    def _compute_hash(data: dict) -> str:
        """Compute SHA-256 hash of data for change detection."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    async def _detect_deletions(
        self, client_id: uuid.UUID, entity_type_id: uuid.UUID, fetched_ids: set[str]
    ) -> int:
        """Soft-delete entities that no longer exist in the external system."""
        if not fetched_ids:
            return 0

        result = await self.db.execute(
            select(AIEntity).where(
                AIEntity.client_id == client_id,
                AIEntity.entity_type_id == entity_type_id,
                AIEntity.is_active == True,
            )
        )
        existing_entities = list(result.scalars().all())

        deleted_count = 0
        for entity in existing_entities:
            if entity.external_id not in fetched_ids:
                await self.knowledge_repo.delete_by_entity(entity.id)
                await self.entity_repo.soft_delete(entity.id)
                deleted_count += 1

        return deleted_count
