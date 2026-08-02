
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.approval_registry import get_approval_registry
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.user import User

router = APIRouter()


class ApprovalSummary(BaseModel):
    approval_id: str
    run_id: str
    code: str
    status: str
    created_at: str


class DecideRequest(BaseModel):
    approved: bool


class DecideResponse(BaseModel):
    approval_id: str
    status: str
    resolved_live: bool


@router.get("/approvals/pending", response_model=list[ApprovalSummary])
def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApprovalSummary]:
    rows = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.user_id == current_user.id, ApprovalRequest.status == "pending")
        .order_by(ApprovalRequest.created_at.desc())
        .all()
    )
    return [
        ApprovalSummary(
            approval_id=r.approval_id,
            run_id=r.run_id,
            code=r.code,
            status=r.status,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/approvals/{approval_id}/decide", response_model=DecideResponse)
def decide_approval(
    approval_id: str,
    req: DecideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DecideResponse:
    record = db.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.user_id != current_user.id:
        # Same shape as every other cross-user lookup in this codebase
        # (see app/agents/run_store.py) — 404, not 403, to avoid confirming
        # the id exists at all to someone who doesn't own it.
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval request already {record.status}")

    resolved_live = get_approval_registry().resolve(approval_id, req.approved)

    record.status = "approved" if req.approved else "rejected"
    record.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return DecideResponse(approval_id=approval_id, status=record.status, resolved_live=resolved_live)