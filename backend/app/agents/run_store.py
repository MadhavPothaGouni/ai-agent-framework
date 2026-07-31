from sqlalchemy.orm import Session

from app.agents.orchestrator import WorkflowResult
from app.models.workflow_run import WorkflowRun, WorkflowStepRecord


def save_run(db: Session, user_id: int, task: str, result: WorkflowResult) -> WorkflowRun:
    run = WorkflowRun(
        run_id=result.run_id,
        user_id=user_id,
        task=task,
        final_decision=result.final_decision,
        attempts=result.attempts,
    )
    db.add(run)
    db.flush()

    for order, step in enumerate(result.steps):
        db.add(
            WorkflowStepRecord(
                workflow_run_id=run.id,
                step_order=order,
                agent=step.agent,
                output=step.output,
                success=step.success,
            )
        )

    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, user_id: int, limit: int = 50) -> list[WorkflowRun]:
    return (
        db.query(WorkflowRun)
        .filter(WorkflowRun.user_id == user_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
        .all()
    )


def get_run(db: Session, user_id: int, run_id: str) -> WorkflowRun | None:
    return (
        db.query(WorkflowRun)
        .filter(WorkflowRun.user_id == user_id, WorkflowRun.run_id == run_id)
        .first()
    )