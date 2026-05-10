"""
Chat router — widget API (public) + admin API (authenticated).

Public endpoints (no JWT required — validated via chatbot_id + session_id):
  POST /chat/session         — start or resume conversation
  POST /chat/stream          — send message, stream SSE response
  GET  /chat/history         — get conversation history
  POST /chat/messages/{id}/react — thumbs up/down/flag

Admin endpoints (JWT required):
  GET  /organizations/{org_id}/conversations — list conversations
  PATCH /organizations/{org_id}/conversations/{id}/resolve
  GET  /organizations/{org_id}/chatbots/{id}/end-users
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.models import ConversationStatus
from app.modules.chat.schemas import (
    StartChatRequest, SendMessageRequest,
    ConversationResponse, MessageResponse, ConversationHistoryResponse,
    EndUserResponse, ReactMessageRequest,
)
from app.modules.chat.service import ChatService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


# ── Widget (Public) ────────────────────────────────────────────────────────────

@router.post("/chat/session", response_model=ConversationResponse)
async def start_chat_session(
    req: StartChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start or resume a conversation. Called by the web widget on page load.
    No authentication required — public endpoint.
    """
    svc = ChatService(db)
    return await svc.start_or_resume(req)


@router.post("/chat/stream")
async def stream_chat(
    request: Request,
    chatbot_id: UUID = Query(...),
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and receive a streaming SSE response.
    Content-Type: text/event-stream

    Query params:
      - chatbot_id: the chatbot to talk to
      - session_id: conversation session identifier

    Body: { "content": "your message", "type": "text" }
    """
    body = await request.json()
    req = SendMessageRequest(**body)
    svc = ChatService(db)

    async def event_generator():
        import json as _rjson
        try:
            async for chunk in svc.stream_chat(session_id, req, chatbot_id):
                yield chunk
        except Exception as _e:
            logger.error(f"Stream generator error: {_e}", exc_info=True)
            yield f"data: {_rjson.dumps({'type': 'error', 'detail': str(_e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx: disable buffering
            "Connection": "keep-alive",
        },
    )


@router.get("/chat/history", response_model=ConversationHistoryResponse)
async def get_chat_history(
    chatbot_id: UUID = Query(...),
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation history for a session."""
    svc = ChatService(db)
    return await svc.get_history(session_id, chatbot_id)


@router.post("/chat/messages/{message_id}/react", status_code=status.HTTP_204_NO_CONTENT)
async def react_to_message(
    message_id: UUID,
    req: ReactMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """React to a message (thumbs_up / thumbs_down / flag)."""
    svc = ChatService(db)
    await svc.react_to_message(message_id, req)


# ── Admin (Authenticated) ──────────────────────────────────────────────────────

@router.get("/organizations/{org_id}/conversations",
            response_model=List[ConversationResponse])
async def list_conversations(
    org_id: UUID,
    chatbot_id: Optional[UUID] = Query(None),
    conv_status: Optional[ConversationStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversations for an organization. Members only."""
    svc = ChatService(db)
    return await svc.list_conversations(
        org_id, requester_id=current_user.id,
        chatbot_id=chatbot_id, conv_status=conv_status,
        limit=limit, offset=offset,
    )


@router.patch("/organizations/{org_id}/conversations/{conv_id}/resolve",
              status_code=status.HTTP_204_NO_CONTENT)
async def resolve_conversation(
    org_id: UUID,
    conv_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a conversation as resolved."""
    svc = ChatService(db)
    await svc.resolve_conversation(org_id, conv_id, requester_id=current_user.id)


@router.get("/organizations/{org_id}/chatbots/{chatbot_id}/end-users",
            response_model=List[EndUserResponse])
async def list_end_users(
    org_id: UUID,
    chatbot_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List end-users (chat visitors) for a chatbot."""
    svc = ChatService(db)
    return await svc.list_end_users(org_id, chatbot_id, requester_id=current_user.id,
                                    limit=limit, offset=offset)
