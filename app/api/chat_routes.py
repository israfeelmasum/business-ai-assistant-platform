"""Chat endpoints - where end-users and agents interact."""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header 
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.client import Client
from app.models.conversation import Conversation
from app.api.deps import get_current_client
from app.schemas.conversation import ChatRequest, ChatResponse, ConversationResponse
from app.services.chat_service import ChatService
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(prefix="/chat", tags=["Chat"])

class AgentReplyRequest(BaseModel):
    message: str

# ==========================================
# 🚀 LAISA'S UPGRADE: Streaming Endpoint
# ==========================================
@router.post("")
async def send_message(
    request: ChatRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get an AI response (Forced Streaming)."""
    service = ChatService(db)
    
    # 🚀 LAISA'S FIX: FORCING STREAMING! 
    # ফ্রন্টএন্ডের ওপর ভরসা না করে আমরা সব সময় স্ট্রিমিং পাঠাব
    return StreamingResponse(
        service.handle_message_stream(client, request), 
        media_type="text/event-stream"
    )

@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for this client."""
    repo = ConversationRepository(db)
    return await repo.get_by_client(client.id, limit=limit, offset=offset)

# ==========================================
# 🚀 LAISA'S FIX: NEW HISTORY API FOR WIDGET POLLING
# ==========================================
@router.get("/history/{session_id}", tags=["Chat"])
async def get_chat_history(
    session_id: str,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Fetch the full message history for a specific session."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.client_id == client.id)
        .where(Conversation.session_id == session_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        return {"messages": []}
        
    return {"messages": conversation.messages}

# ==========================================
# NEW ADMIN/AGENT ENDPOINTS
# ==========================================
@router.get("/escalated", response_model=list[ConversationResponse])
async def get_escalated_conversations(
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations waiting for human agent."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.client_id == client.id, Conversation.status == 'human_escalated')
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())

@router.post("/{conversation_id}/agent-reply")
async def agent_reply(
    conversation_id: uuid.UUID,
    request: AgentReplyRequest,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Human agent replies to an escalated chat."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.client_id != client.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    now = datetime.now(timezone.utc).isoformat()
    # 🚀 FIX: "agent" রোলে ফেরত আনা হলো, যাতে অ্যাডমিন প্যানেলে ডানদিকে সবুজ বক্সে দেখায়
    updated_messages = conversation.messages + [
        {"role": "agent", "content": request.message, "timestamp": now}
    ]

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(messages=updated_messages)
    )
    await db.commit()
    return {"success": True, "message": "Reply saved successfully"}

@router.delete("/conversations/{conversation_id}", tags=["Chat"])
async def delete_conversation(
    conversation_id: uuid.UUID,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete an escalated or resolved conversation."""
    # Verify ownership before deletion to ensure high security
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.client_id != client.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Direct DB delete for maximum speed
    await db.execute(
        delete(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.client_id == client.id)
    )
    await db.commit()
    return {"message": "Chat permanently deleted"}

# ==========================================
# 🚀 CORE SYSTEM: Dynamic Client Configuration
# ==========================================
@router.patch("/config", tags=["Client Config"])
async def update_client_config(
    config_update: dict,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Update the client's AI engine configuration directly from the dashboard."""
    
    # 1. (Fetch existing config to prevent overwriting)
    existing_config = current_client.config or {}
    
    # 2. (Merge new data with existing)
    existing_config.update(config_update)
    
    # 3. (Update in DB)
    await db.execute(
        update(Client)
        .where(Client.id == current_client.id)
        .values(config=existing_config)
    )
    await db.commit()
    
    return {"status": "success", "message": "Configuration successfully synced to Cloud DB"}
    
# ==========================================
# 🚀 PRO-LEVEL: LMS Auto Sync (Vector DB Integration)
# ==========================================
@router.post("/sync-lms", tags=["Data Sync"])
async def sync_lms_data(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Fetch external LMS data and embed it into the AI Vector Database."""
    from app.core.ai_client import ai_client
    
    # 🚀 FIX: Ensure AIKnowledge is correctly imported
    try:
        from app.models.ai_knowledge import AIKnowledge
    except ImportError:
        raise HTTPException(status_code=500, detail="Database model AIKnowledge not found.")

    try:
        # 1. 🌐 MOCK External LMS API Call (In production, replace with actual requests.get to ICT BD LMS)
        mock_lms_data = [
            {"title": "Python Pro", "desc": "A 3-month program taught by Mahinur Rahaman. Certificate provided upon completion.", "price": "10,000 BDT"},
            {"title": "Professional AI Engineer", "desc": "Learn generative AI engineering and deployment.", "price": "10,000 BDT (discounted from 20,000 BDT)"},
            {"title": "FastAPI Backend Pro", "desc": "3-month online program led by Mr. LAISA. Auto-synchronizes with our platform.", "price": "15,000 BDT"}
        ]
        
        sync_count = 0
        for course in mock_lms_data:
            # 2. 🧠 Prepare Text for Vector DB
            content_text = f"Course Name: {course['title']}\nPrice: {course['price']}\nDetails: {course['desc']}"
            
            # 3. 🔢 Generate Vector Embedding via AI Client
            embedding = await ai_client.generate_embedding(content_text)
            
            # 4. 💾 Save to Knowledge Repository
            new_knowledge = AIKnowledge(
                client_id=current_client.id,
                content=content_text,
                summary=f"Course Details: {course['title']}",
                embedding=embedding,
                meta_data={"source": "LMS_Auto_Sync", "type": "course"}
            )
            db.add(new_knowledge)
            sync_count += 1
            
        await db.commit()
        return {"status": "success", "message": f"{sync_count} courses dynamically embedded and synced to Vector DB!"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"LMS Sync Error: {str(e)}") 
        
# ==========================================
# 🎨 WIDGET CONFIGURATION API (Public)
# ==========================================
@router.get("/widget-config", tags=["Widget"])
async def get_widget_config(
    x_api_key: str = Header(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch dynamic configuration (like logo and welcome message) for the chatbot widget.
    """
    # 🚀 Async Database Query
    result = await db.execute(
        select(Client).where(Client.api_key == x_api_key)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    return {
        "bot_logo": client.logo_base64,
        "welcome_message": client.welcome_message,
        "company_name": client.name
    }
    