from app.agents import run_store
from app.agents.orchestrator import WorkflowResult, WorkflowStep
from app.core.security import hash_password
from app.models.user import User


def _make_user(db_session, email: str) -> User:
    user = User(email=email, hashed_password=hash_password("pw"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _fake_result(run_id: str = "run-1") -> WorkflowResult:
    return WorkflowResult(
        run_id=run_id,
        steps=[
            WorkflowStep("planner", "plan output", True),
            WorkflowStep("coder", "code output", True),
            WorkflowStep("tester", "1 passed", True),
            WorkflowStep("reviewer", "Review decision: approved.", True),
        ],
        final_decision="approved",
        attempts=1,
    )


def test_save_and_get_run_round_trip(db_session):
    user = _make_user(db_session, "run-store@example.com")

    saved = run_store.save_run(db_session, user.id, "build a calculator", _fake_result("run-abc"))
    assert saved.run_id == "run-abc"
    assert len(saved.steps) == 4

    fetched = run_store.get_run(db_session, user.id, "run-abc")
    assert fetched is not None
    assert fetched.task == "build a calculator"
    assert [s.agent for s in fetched.steps] == ["planner", "coder", "tester", "reviewer"]


def test_list_runs_scoped_to_user_and_ordered_newest_first(db_session):
    user_a = _make_user(db_session, "run-store-a@example.com")
    user_b = _make_user(db_session, "run-store-b@example.com")

    run_store.save_run(db_session, user_a.id, "task 1", _fake_result("run-a1"))
    run_store.save_run(db_session, user_a.id, "task 2", _fake_result("run-a2"))
    run_store.save_run(db_session, user_b.id, "task 3", _fake_result("run-b1"))

    runs_a = run_store.list_runs(db_session, user_a.id)
    assert [r.run_id for r in runs_a] == ["run-a2", "run-a1"]

    runs_b = run_store.list_runs(db_session, user_b.id)
    assert [r.run_id for r in runs_b] == ["run-b1"]


def test_get_run_returns_none_for_other_users_run(db_session):
    user_a = _make_user(db_session, "run-store-c@example.com")
    user_b = _make_user(db_session, "run-store-d@example.com")

    run_store.save_run(db_session, user_a.id, "private task", _fake_result("run-private"))

    assert run_store.get_run(db_session, user_b.id, "run-private") is None
    assert run_store.get_run(db_session, user_a.id, "run-private") is not None

def test_save_run_persists_usage_events_as_usage_records(db_session):
    from app.core.cost_tracker import UsageEvent
    from app.models.usage import UsageRecord

    user = _make_user(db_session, "run-store-usage@example.com")

    result = _fake_result("run-usage-1")
    result.usage_events = [
        UsageEvent(agent="planner", provider="mock", input_tokens=10, output_tokens=5, cost_usd=0.0),
        UsageEvent(agent="coder", provider="mock", input_tokens=40, output_tokens=30, cost_usd=0.0),
    ]

    run_store.save_run(db_session, user.id, "build a calculator", result)

    records = db_session.query(UsageRecord).filter(UsageRecord.run_id == "run-usage-1").all()
    assert len(records) == 2
    assert {r.agent for r in records} == {"planner", "coder"}
    assert all(r.user_id == user.id for r in records)


def test_save_run_persists_cost_totals_on_the_run_row(db_session):
    user = _make_user(db_session, "run-store-totals@example.com")

    result = _fake_result("run-totals-1")
    result.total_cost_usd = 0.1234
    result.total_tokens = 999

    saved = run_store.save_run(db_session, user.id, "build a calculator", result)

    assert saved.total_cost_usd == 0.1234
    assert saved.total_tokens == 999