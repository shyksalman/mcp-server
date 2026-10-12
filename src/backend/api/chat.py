from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.agent.conversation import ChatHistory, ChatRequest, ChatResponse
from backend.agent.memory import ConversationMemory
from backend.dependencies import chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def post_chat(payload: ChatRequest, memory: ConversationMemory = Depends(chat)) -> ChatResponse:
    try:
        conversation_id, message = await memory.ask(payload.message, payload.conversation_id)
        return ChatResponse(message=message, conversation_id=conversation_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat/confirm/{action_id}", response_model=ChatResponse)
async def confirm_action(
    action_id: str,
    conversation_id: UUID | None = None,
    memory: ConversationMemory = Depends(chat),
) -> ChatResponse:
    normalized_id, message = await memory.confirm(action_id, conversation_id)
    return ChatResponse(message=message, conversation_id=normalized_id)


@router.get("/chat/{conversation_id}", response_model=ChatHistory)
async def get_chat_history(
    conversation_id: UUID, memory: ConversationMemory = Depends(chat)
) -> ChatHistory:
    messages = await memory.history(conversation_id)
    return ChatHistory(conversation_id=conversation_id, messages=messages)


@router.delete("/chat/{conversation_id}", status_code=204)
async def clear_chat(
    conversation_id: UUID, memory: ConversationMemory = Depends(chat)
) -> Response:
    await memory.clear(conversation_id)
    return Response(status_code=204)
