from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.orchestrator import DevWorkflow
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class WorkflowRequest(BaseModel):
    task: str


class WorkflowStepResponse(BaseModel):
    agent: str
    output: str
    success: bool


class WorkflowResponse(BaseModel):
    steps: list[WorkflowStepResponse]
    final_decision: str
    attempts: int


@router.post("/run", response_model=WorkflowResponse)
def run_workflow(req: WorkflowRequest, current_user: User = Depends(get_current_user)) -> WorkflowResponse:
    result = DevWorkflow().run(req.task)
    return WorkflowResponse(
        steps=[
            WorkflowStepResponse(agent=s.agent, output=s.output, success=s.success)
            for s in result.steps
        ],
        final_decision=result.final_decision,
        attempts=result.attempts,
    )