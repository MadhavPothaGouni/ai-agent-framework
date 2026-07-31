from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, current_user: User = Depends(get_current_user)) -> ChatResponse:
    # TODO(phase2): replace with agent orchestrator call
    return ChatResponse(reply=f"echo: {req.message}", session_id=req.session_id)