
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.budget import BudgetLimit
from app.models.usage import UsageRecord

# Generous enough that nobody using the mock provider (which is always
# free) is ever silently blocked out of the box.
DEFAULT_MONTHLY_CAP_USD = 5.0


@dataclass
class BudgetStatus:
    monthly_cap_usd: float
    spent_this_month_usd: float
    remaining_usd: float
    exceeded: bool


def _month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def get_monthly_cap(db: Session, user_id: int) -> float:
    row = db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id).first()
    return row.monthly_cap_usd if row is not None else DEFAULT_MONTHLY_CAP_USD


def set_monthly_cap(db: Session, user_id: int, monthly_cap_usd: float) -> BudgetLimit:
    row = db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id).first()
    if row is None:
        row = BudgetLimit(user_id=user_id, monthly_cap_usd=monthly_cap_usd)
        db.add(row)
    else:
        row.monthly_cap_usd = monthly_cap_usd
    db.commit()
    db.refresh(row)
    return row


def spent_this_month(db: Session, user_id: int) -> float:
    rows = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id, UsageRecord.created_at >= _month_start())
        .all()
    )
    return round(sum(r.cost_usd for r in rows), 8)


def get_budget_status(db: Session, user_id: int, additional_cost: float = 0.0) -> BudgetStatus:
    cap = get_monthly_cap(db, user_id)
    spent = spent_this_month(db, user_id) + additional_cost
    return BudgetStatus(
        monthly_cap_usd=cap,
        spent_this_month_usd=round(spent, 8),
        remaining_usd=round(cap - spent, 8),
        exceeded=spent >= cap,
    )


def make_budget_checker(db: Session, user_id: int):
    """Returns a closure DevWorkflow.run() calls as
    check_budget_exceeded(additional_cost_so_far_this_run) -> bool.
    """

    def check(additional_cost_so_far: float) -> bool:
        return get_budget_status(db, user_id, additional_cost_so_far).exceeded

    return check