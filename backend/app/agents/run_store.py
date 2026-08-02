
from sqlalchemy.orm import Session

from app.agents.orchestrator import WorkflowResult
from app.models.usage import UsageRecord
from app.models.workflow_run import WorkflowRun, WorkflowStepRecord


def save_run(db: Session, user_id: int, task: str, result: WorkflowResult) -> WorkflowRun:
    run = WorkflowRun(
        run_id=result.run_id,
        user_id=user_id,
        task=task,
        final_decision=result.final_decision,
        attempts=result.attempts,
        total_cost_usd=result.total_cost_usd,
        total_tokens=result.total_tokens,
    )
    db.add(run)
    db.flush()  # assigns run.id without committing yet, so steps can reference it

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

    for event in result.usage_events:
        db.add(
            UsageRecord(
                run_id=result.run_id,
                user_id=user_id,
                agent=event.agent,
                provider=event.provider,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                cost_usd=event.cost_usd,
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