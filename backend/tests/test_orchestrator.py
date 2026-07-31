from app.agents.orchestrator import DevWorkflow
from app.agents.tester import TesterAgent


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