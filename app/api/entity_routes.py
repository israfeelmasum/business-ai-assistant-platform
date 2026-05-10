"""
Entity sync endpoints - called by external systems to push data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.client import Client
from app.api.deps import get_current_client
from app.schemas.entity import (
    EntitySyncRequest,
    EntitySyncResponse,
    EntityTypeResponse,
    BulkEntitySyncRequest,
    BulkEntitySyncResponse,
)
from app.services.entity_sync_service import EntitySyncService
from app.repositories.entity_type_repository import EntityTypeRepository
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entities", tags=["Entity Sync"])


@router.post("/sync", response_model=EntitySyncResponse)
async def sync_entity(
    request: EntitySyncRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Sync a single entity. Entity type is auto-created if new."""
    service = EntitySyncService(db)
    return await service.sync(client, request)


@router.post("/sync/bulk", response_model=BulkEntitySyncResponse)
async def sync_entities_bulk(
    request: BulkEntitySyncRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Sync multiple entities at once (max 100)."""
    service = EntitySyncService(db)
    results = []
    succeeded = 0
    failed = 0

    for entity_request in request.entities:
        try:
            result = await service.sync(client, entity_request)
            results.append(result)
            succeeded += 1
        except Exception as e:
            results.append(EntitySyncResponse(
                success=False,
                message=str(e),
                entity_id=entity_request.entity_id,
                entity_type=entity_request.entity_type,
                action=entity_request.action,
            ))
            failed += 1

    return BulkEntitySyncResponse(
        success=failed == 0,
        total=len(request.entities),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


@router.get("/types", response_model=list[EntityTypeResponse])
async def get_entity_types(
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get entity types for chat UI quick-select buttons."""
    repo = EntityTypeRepository(db)
    return await repo.get_by_client(client.id)


# =========================================================================
# 🚀 NEW: Real-Time Auto Sync Webhook with Email Notification
# =========================================================================
@router.post("/webhook-sync", summary="Real-Time Auto Sync for External Systems")
async def real_time_webhook_sync(
    request: EntitySyncRequest,
    background_tasks: BackgroundTasks,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook Endpoint for Main System.
    When a database insert/update/delete happens in the main system, 
    it calls this endpoint to auto-train the AI and notify the admin.
    """
    service = EntitySyncService(db)
    
    try:
        # Step 1: AI Brain Update (Vector DB Sync)
        sync_result = await service.sync(client, request)
        
        # Step 2: Prepare Email Notification Content
        action_verb = {
            "create": "Added to",
            "update": "Updated in",
            "delete": "Deleted from"
        }.get(request.action.lower(), request.action)
        
        # Extract name/title safely from data payload
        entity_name = request.entity_id
        if request.data:
            entity_name = request.data.get("title", request.data.get("name", request.entity_id))
        
        subject = f"🚀 AI Knowledge Auto-Updated: {request.entity_type.capitalize()} {action_verb}"
        content = f"""
        Hello Admin,

        A new database event was detected from the Main System. 
        The AI Chatbot has automatically intercepted it and updated its Vector Brain.

        📊 EVENT DETAILS:
        -------------------------------------------
        • Entity Type: {request.entity_type.upper()}
        • Entity Name: {entity_name}
        • Action: {request.action.upper()}
        • Target Client: {client.name}
        -------------------------------------------
        
        ✅ Status: Success. The AI is now ready to answer queries based on this new data.
        No manual intervention is required.

        Regards,
        Fellow Technology
        """
        
        # Step 3: Send Email in Background (so API response is instant)
        background_tasks.add_task(
            email_service.send_notification,
            subject=subject,
            content=content
        )
        
        logger.info(f"Webhook Sync Successful for {request.entity_type} - {request.entity_id}")
        return {
            "status": "success", 
            "message": "AI automatically synced and admin notified.", 
            "details": {"entity_id": request.entity_id, "action": request.action}
        }

    except Exception as e:
        logger.error(f"Webhook Sync Failed: {e}")
        
        # Notify admin about the failure too!
        background_tasks.add_task(
            email_service.send_notification,
            subject=f"⚠️ URGENT: AI Auto-Sync Failed!",
            content=f"Failed to sync {request.entity_type} (ID: {request.entity_id}).\nError: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e)) 
        

# =========================================================================
# 🚀 PRO-LEVEL: Fetch Data from External Client URL (Dynamic Migration)
# =========================================================================
from pydantic import BaseModel, HttpUrl
import httpx 
from app.schemas.entity import EntitySyncRequest # আপনার নিজের স্কিমা ইমপোর্ট করা হলো

class ExternalSyncRequest(BaseModel):
    api_url: HttpUrl
    entity_type: str = "course" # Default type changed to match your context

@router.post("/sync/external-url", tags=["Entity Sync"])
async def sync_from_external_url(
    request: ExternalSyncRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Fetch data from client's custom API URL and inject into Vector DB securely."""
    try:
        # 1. Fetch JSON data from the client's provided URL
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(str(request.api_url), timeout=15.0)
            response.raise_for_status()
            external_data = response.json()
            
        if isinstance(external_data, dict):
            external_data = [external_data]
            
        if not isinstance(external_data, list):
            raise ValueError("Target API must return a JSON Array/List.")

        # 2. Use your bulletproof EntitySyncService!
        service = EntitySyncService(db)
        sync_count = 0
        
        for i, item in enumerate(external_data):
            # Try to find a unique ID from the external data, or generate one
            ext_id = str(item.get("id", item.get("course_id", item.get("uuid", f"auto_ext_{i}"))))
            
            # Create a properly formatted request for your robust sync service
            sync_req = EntitySyncRequest(
                entity_id=ext_id,
                entity_type=request.entity_type,
                action="create",
                data=item
            )
            
            # Let your existing, tested service handle the DB relationships and Vector embeddings!
            await service.sync(client, sync_req)
            sync_count += 1
            
        return {"status": "success", "message": f"{sync_count} items securely synced to {client.name}'s AI Knowledge Base!"}

    except Exception as e:
        logger.error(f"External Sync Failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch or process data: {str(e)}")