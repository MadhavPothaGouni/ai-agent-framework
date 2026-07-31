import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.planner import PlannerAgent
from app.core.security import get_current_user
from app.db.session import get_db
from app.memory import manager as memory
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())

    memory.save_message(db, session_id, current_user.id, "user", req.message)
    history = memory.get_history(db, session_id, current_user.id)

    context = AgentContext(task=req.message, history=history)
    result = PlannerAgent().run(context)

    memory.save_message(db, session_id, current_user.id, "assistant", result.output)

    return ChatResponse(reply=result.output, session_id=session_id)