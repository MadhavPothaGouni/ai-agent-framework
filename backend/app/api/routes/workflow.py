from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import run_store
from app.agents.orchestrator import DevWorkflow
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter()


class WorkflowRequest(BaseModel):
    task: str


class WorkflowStepResponse(BaseModel):
    agent: str
    output: str
    success: bool


class WorkflowResponse(BaseModel):
    run_id: str
    steps: list[WorkflowStepResponse]
    final_decision: str
    attempts: int


class WorkflowRunSummary(BaseModel):
    run_id: str
    task: str
    final_decision: str
    attempts: int
    created_at: str


class WorkflowRunDetail(WorkflowRunSummary):
    steps: list[WorkflowStepResponse]


@router.post("/run", response_model=WorkflowResponse)
def run_workflow(
    req: WorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    result = DevWorkflow().run(req.task)
    run_store.save_run(db, current_user.id, req.task, result)

    return WorkflowResponse(
        run_id=result.run_id,
        steps=[
            WorkflowStepResponse(agent=s.agent, output=s.output, success=s.success)
            for s in result.steps
        ],
        final_decision=result.final_decision,
        attempts=result.attempts,
    )


@router.get("/runs", response_model=list[WorkflowRunSummary])
def list_workflow_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkflowRunSummary]:
    runs = run_store.list_runs(db, current_user.id)
    return [
        WorkflowRunSummary(
            run_id=r.run_id,
            task=r.task,
            final_decision=r.final_decision,
            attempts=r.attempts,
            created_at=r.created_at.isoformat(),
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=WorkflowRunDetail)
def get_workflow_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowRunDetail:
    run = run_store.get_run(db, current_user.id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return WorkflowRunDetail(
        run_id=run.run_id,
        task=run.task,
        final_decision=run.final_decision,
        attempts=run.attempts,
        created_at=run.created_at.isoformat(),
        steps=[
            WorkflowStepResponse(agent=s.agent, output=s.output, success=s.success)
            for s in run.steps
        ],
    )