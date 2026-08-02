from pathlib import Path

from app.agents.orchestrator import DevWorkflow
from app.agents.tester import TesterAgent


def test_workflow_happy_path_runs_all_agents_in_order():
    result = DevWorkflow().run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    # No "debugger" step when the first attempt passes — it only runs on failure.
    assert agent_order == ["planner", "coder", "tester", "security_auditor", "reviewer"]
    assert result.attempts == 1
    assert result.final_decision == "approved"


def test_workflow_security_auditor_flags_mock_solution_as_clean():
    """The mock provider's fixed solution.py has no dangerous calls, secrets,
    or SQL string-building — the audit should pass it with no findings."""
    result = DevWorkflow().run("build a calculator")

    security_step = next(s for s in result.steps if s.agent == "security_auditor")
    assert security_step.success is True
    assert security_step.metadata["high_severity_count"] == 0


def test_workflow_writes_real_files_and_runs_real_pytest():
    """With the default (no injected check_fn) Tester, the workflow should
    actually write solution.py + test_solution.py to disk and run a real
    pytest subprocess against them — not just simulate success.
    """
    result = DevWorkflow().run("build a calculator")

    tester_step = next(s for s in result.steps if s.agent == "tester")
    coder_step = next(s for s in result.steps if s.agent == "coder")

    assert "pytest_output" in tester_step.metadata
    assert "passed" in tester_step.metadata["pytest_output"]

    workspace_dir = Path(coder_step.metadata["file_path"]).parent
    assert (workspace_dir / "solution.py").exists()
    assert (workspace_dir / "test_solution.py").exists()
    assert "def solution" in (workspace_dir / "solution.py").read_text()


def test_workflow_retries_coder_when_tester_fails_then_succeeds():
    calls = {"count": 0}

    def flaky_check(code: str) -> bool:
        calls["count"] += 1
        return calls["count"] >= 2  # fail first attempt, pass second

    workflow = DevWorkflow(max_attempts=3, tester=TesterAgent(check_fn=flaky_check))
    result = workflow.run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    # First attempt fails -> debugger runs and hands a diagnosis to the
    # next coder attempt; second attempt passes -> no second debugger call.
    assert agent_order == [
        "planner",
        "coder",
        "tester",
        "debugger",
        "coder",
        "tester",
        "security_auditor",
        "reviewer",
    ]
    assert result.attempts == 2
    assert result.final_decision == "approved"


def test_workflow_debugger_feeds_diagnosis_to_next_coder_attempt():
    """The Coder's second-attempt prompt should be built from the Debugger's
    structured diagnosis, not the raw pytest failure text."""
    calls = {"count": 0}

    def flaky_check(code: str) -> bool:
        calls["count"] += 1
        return calls["count"] >= 2

    workflow = DevWorkflow(max_attempts=3, tester=TesterAgent(check_fn=flaky_check))
    result = workflow.run("build a calculator")

    debugger_step = next(s for s in result.steps if s.agent == "debugger")
    assert "Diagnosis:" in debugger_step.output


def test_workflow_gives_up_after_max_attempts():
    workflow = DevWorkflow(max_attempts=2, tester=TesterAgent(check_fn=lambda code: False))
    result = workflow.run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    assert agent_order == [
        "planner",
        "coder",
        "tester",
        "debugger",
        "coder",
        "tester",
        "debugger",
        "security_auditor",
        "reviewer",
    ]
    assert result.attempts == 2
    assert result.final_decision == "changes_requested"


def test_workflow_on_step_callback_fires_for_every_step_in_order():
    """This is what app/api/routes/workflow_ws.py relies on to stream
    progress live instead of the caller blocking for the whole run."""
    seen = []

    result = DevWorkflow().run("build a calculator", on_step=seen.append)

    assert [s.agent for s in seen] == [s.agent for s in result.steps]
    assert seen == result.steps


def test_workflow_on_step_callback_is_optional():
    # Should not raise when omitted (the default REST /workflow/run path).
    result = DevWorkflow().run("build a calculator")
    assert result.final_decision == "approved"

# Human-in-the-loop approval gate

def test_workflow_without_require_approval_never_adds_human_review_step():
    result = DevWorkflow().run("build a calculator")
    assert "human_review" not in [s.agent for s in result.steps]


def test_workflow_pauses_for_approval_and_continues_when_approved():
    seen = []

    def approve_everything(approval_id: str, step) -> bool:
        seen.append((approval_id, step.agent))
        return True

    result = DevWorkflow().run(
        "build a calculator",
        require_approval=True,
        on_approval_required=approve_everything,
    )

    agent_order = [s.agent for s in result.steps]
    assert agent_order == ["planner", "coder", "human_review", "tester", "security_auditor", "reviewer"]
    assert len(seen) == 1
    assert seen[0][1] == "coder"
    assert result.final_decision == "approved"

    human_review_step = next(s for s in result.steps if s.agent == "human_review")
    assert human_review_step.success is True


def test_workflow_stops_immediately_when_human_rejects():
    result = DevWorkflow().run(
        "build a calculator",
        require_approval=True,
        on_approval_required=lambda approval_id, step: False,
    )

    agent_order = [s.agent for s in result.steps]
    # Rejected before the Tester ever runs -> no tester, no debugger, no
    # security_auditor step (there's nothing to test or scan).
    assert agent_order == ["planner", "coder", "human_review", "reviewer"]
    assert result.final_decision == "changes_requested"

    human_review_step = next(s for s in result.steps if s.agent == "human_review")
    assert human_review_step.success is False
    assert "Rejected" in human_review_step.output


def test_workflow_require_approval_without_callback_behaves_like_no_gate():
    """require_approval=True with no callback provided shouldn't crash — it
    should just run normally, as if the gate wasn't requested at all."""
    result = DevWorkflow().run("build a calculator", require_approval=True, on_approval_required=None)

    assert "human_review" not in [s.agent for s in result.steps]
    assert result.final_decision == "approved"


# Budget enforcement + cost tracking


def test_workflow_records_usage_and_totals_even_with_free_mock_provider():
    result = DevWorkflow().run("build a calculator")

    # Mock provider is free, but usage is still measured (nonzero tokens),
    # just at $0 cost — cost tracking isn't a no-op just because nothing
    # cost real money.
    assert result.total_tokens > 0
    assert result.total_cost_usd == 0.0
    assert len(result.usage_events) >= 2  # at least planner + coder called the provider
    assert {e.agent for e in result.usage_events} >= {"planner", "coder"}


def test_workflow_blocks_before_planner_when_already_over_budget():
    result = DevWorkflow().run("build a calculator", check_budget_exceeded=lambda additional: True)

    assert [s.agent for s in result.steps] == ["budget_guard"]
    assert result.final_decision == "budget_exceeded"
    assert result.attempts == 0
    assert result.total_cost_usd == 0.0

    guard_step = result.steps[0]
    assert guard_step.success is False
    assert "budget" in guard_step.output.lower()


def test_workflow_runs_normally_when_check_budget_exceeded_always_false():
    result = DevWorkflow().run("build a calculator", check_budget_exceeded=lambda additional: False)

    assert "budget_guard" not in [s.agent for s in result.steps]
    assert result.final_decision == "approved"


def test_workflow_mid_run_circuit_breaker_stops_retries_after_first_failure():
    """Budget looks fine before the run starts, but becomes exceeded the
    moment the first attempt's cost is counted — the workflow should stop
    retrying (no second Coder/Tester attempt) but still finish the pipeline
    (security_auditor + reviewer) with whatever it has."""
    calls = {"count": 0}

    def always_fails(code: str) -> bool:
        calls["count"] += 1
        return False

    seen_additional_costs = []

    def check_budget_exceeded(additional_cost_so_far: float) -> bool:
        seen_additional_costs.append(additional_cost_so_far)
        return len(seen_additional_costs) >= 2  # allow the pre-run check, block after attempt 1

    workflow = DevWorkflow(max_attempts=5, tester=TesterAgent(check_fn=always_fails))
    result = workflow.run("build a calculator", check_budget_exceeded=check_budget_exceeded)

    agent_order = [s.agent for s in result.steps]
    assert agent_order == [
        "planner",
        "coder",
        "tester",
        "debugger",
        "budget_guard",
        "security_auditor",
        "reviewer",
    ]
    assert result.attempts == 1  # never got to attempt 2
    assert calls["count"] == 1
    assert result.final_decision == "changes_requested"


def test_workflow_without_budget_checker_never_adds_budget_guard_step():
    result = DevWorkflow().run("build a calculator")
    assert "budget_guard" not in [s.agent for s in result.steps]