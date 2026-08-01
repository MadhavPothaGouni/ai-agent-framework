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