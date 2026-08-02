
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import budget as budget_service
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter()


class BudgetStatusResponse(BaseModel):
    monthly_cap_usd: float
    spent_this_month_usd: float
    remaining_usd: float
    exceeded: bool


class SetBudgetRequest(BaseModel):
    monthly_cap_usd: float = Field(gt=0, description="Must be a positive USD amount")


@router.get("/status", response_model=BudgetStatusResponse)
def get_budget_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetStatusResponse:
    status = budget_service.get_budget_status(db, current_user.id)
    return BudgetStatusResponse(**status.__dict__)


@router.put("/limit", response_model=BudgetStatusResponse)
def set_budget_limit(
    req: SetBudgetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetStatusResponse:
    budget_service.set_monthly_cap(db, current_user.id, req.monthly_cap_usd)
    status = budget_service.get_budget_status(db, current_user.id)
    return BudgetStatusResponse(**status.__dict__)