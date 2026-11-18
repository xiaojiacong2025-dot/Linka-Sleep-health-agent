from __future__ import annotations

from fastapi import APIRouter, Request

from sleep_agent.schemas import ChatRequest, ChatResponse


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    return request.app.state.agent.invoke(
        payload.message, payload.conversation_id, payload.reference_time
    )

