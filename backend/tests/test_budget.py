from app.agents import budget
from app.core.security import hash_password
from app.models.usage import UsageRecord
from app.models.user import User


def _make_user(db_session, email: str) -> User:
    user = User(email=email, hashed_password=hash_password("pw"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_default_cap_applies_when_none_set(db_session):
    user = _make_user(db_session, "budget-default@example.com")
    assert budget.get_monthly_cap(db_session, user.id) == budget.DEFAULT_MONTHLY_CAP_USD


def test_set_monthly_cap_persists_and_is_read_back(db_session):
    user = _make_user(db_session, "budget-set@example.com")
    budget.set_monthly_cap(db_session, user.id, 25.0)
    assert budget.get_monthly_cap(db_session, user.id) == 25.0


def test_set_monthly_cap_twice_updates_in_place(db_session):
    user = _make_user(db_session, "budget-update@example.com")
    budget.set_monthly_cap(db_session, user.id, 10.0)
    budget.set_monthly_cap(db_session, user.id, 20.0)
    assert budget.get_monthly_cap(db_session, user.id) == 20.0


def test_spent_this_month_sums_usage_records(db_session):
    user = _make_user(db_session, "budget-spend@example.com")
    db_session.add(
        UsageRecord(
            run_id="r1", user_id=user.id, agent="planner", provider="anthropic",
            input_tokens=100, output_tokens=50, cost_usd=1.5,
        )
    )
    db_session.add(
        UsageRecord(
            run_id="r1", user_id=user.id, agent="coder", provider="anthropic",
            input_tokens=200, output_tokens=100, cost_usd=2.5,
        )
    )
    db_session.commit()

    assert budget.spent_this_month(db_session, user.id) == 4.0


def test_spent_this_month_is_scoped_per_user(db_session):
    user_a = _make_user(db_session, "budget-scope-a@example.com")
    user_b = _make_user(db_session, "budget-scope-b@example.com")
    db_session.add(
        UsageRecord(
            run_id="r1", user_id=user_a.id, agent="planner", provider="anthropic",
            input_tokens=100, output_tokens=50, cost_usd=3.0,
        )
    )
    db_session.commit()

    assert budget.spent_this_month(db_session, user_a.id) == 3.0
    assert budget.spent_this_month(db_session, user_b.id) == 0.0


def test_budget_status_not_exceeded_when_under_cap(db_session):
    user = _make_user(db_session, "budget-status-ok@example.com")
    budget.set_monthly_cap(db_session, user.id, 10.0)

    status = budget.get_budget_status(db_session, user.id)
    assert status.monthly_cap_usd == 10.0
    assert status.spent_this_month_usd == 0.0
    assert status.remaining_usd == 10.0
    assert status.exceeded is False


def test_budget_status_exceeded_when_spend_meets_cap(db_session):
    user = _make_user(db_session, "budget-status-exceeded@example.com")
    budget.set_monthly_cap(db_session, user.id, 5.0)
    db_session.add(
        UsageRecord(
            run_id="r1", user_id=user.id, agent="planner", provider="anthropic",
            input_tokens=100, output_tokens=50, cost_usd=5.0,
        )
    )
    db_session.commit()

    status = budget.get_budget_status(db_session, user.id)
    assert status.exceeded is True
    assert status.remaining_usd == 0.0


def test_budget_status_accounts_for_additional_cost_not_yet_persisted(db_session):
    """This is what lets DevWorkflow's mid-run circuit breaker (see
    app/agents/orchestrator.py) catch a run that would go over budget
    before its own usage has been written to usage_records yet."""
    user = _make_user(db_session, "budget-status-inflight@example.com")
    budget.set_monthly_cap(db_session, user.id, 5.0)

    status = budget.get_budget_status(db_session, user.id, additional_cost=6.0)
    assert status.exceeded is True
    assert status.spent_this_month_usd == 6.0


def test_make_budget_checker_reflects_live_status(db_session):
    user = _make_user(db_session, "budget-checker@example.com")
    budget.set_monthly_cap(db_session, user.id, 5.0)
    checker = budget.make_budget_checker(db_session, user.id)

    assert checker(0.0) is False
    assert checker(5.0) is True