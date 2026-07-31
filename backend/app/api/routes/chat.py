"""Chat endpoint — routes a user message to the agent orchestrator.

Phase 1 stub — returns an echo response. Wire this up to
app.agents once the Planner/Coding agents exist.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # TODO(phase2): replace with agent orchestrator call
    return ChatResponse(reply=f"echo: {req.message}", session_id=req.session_id)
