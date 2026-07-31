from app.agents.orchestrator import DevWorkflow
from app.agents.tester import TesterAgent
from pathlib import Path

def test_workflow_happy_path_runs_all_agents_in_order():
    result = DevWorkflow().run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    assert agent_order == ["planner", "coder", "tester", "reviewer"]
    assert result.attempts == 1
    assert result.final_decision == "approved"


def test_workflow_retries_coder_when_tester_fails_then_succeeds():
    calls = {"count": 0}

    def flaky_check(code: str) -> bool:
        calls["count"] += 1
        return calls["count"] >= 2  # fail first attempt, pass second

    workflow = DevWorkflow(max_attempts=3, tester=TesterAgent(check_fn=flaky_check))
    result = workflow.run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    assert agent_order == ["planner", "coder", "tester", "coder", "tester", "reviewer"]
    assert result.attempts == 2
    assert result.final_decision == "approved"


def test_workflow_gives_up_after_max_attempts():
    workflow = DevWorkflow(max_attempts=2, tester=TesterAgent(check_fn=lambda code: False))
    result = workflow.run("build a calculator")

    agent_order = [s.agent for s in result.steps]
    assert agent_order == ["planner", "coder", "tester", "coder", "tester", "reviewer"]
    assert result.attempts == 2
    assert result.final_decision == "changes_requested"

def test_workflow_writes_real_files_and_runs_real_pytest():
    result = DevWorkflow().run("build a calculator")

    tester_step = next(s for s in result.steps if s.agent == "tester")
    coder_step = next(s for s in result.steps if s.agent == "coder")

    assert "pytest_output" in tester_step.metadata
    assert "passed" in tester_step.metadata["pytest_output"]

    workspace_dir = Path(coder_step.metadata["file_path"]).parent
    assert (workspace_dir / "solution.py").exists()
    assert (workspace_dir / "test_solution.py").exists()
    assert "def solution" in (workspace_dir / "solution.py").read_text()