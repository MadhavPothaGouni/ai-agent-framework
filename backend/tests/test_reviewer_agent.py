from app.agents.base import AgentContext
from app.agents.reviewer import ReviewerAgent


def test_approves_when_tests_and_security_both_pass():
    context = AgentContext(task="t")
    context.memory["test_passed"] = True
    context.memory["security_passed"] = True

    result = ReviewerAgent().run(context)

    assert result.success is True
    assert context.memory["review_decision"] == "approved"


def test_rejects_when_tests_fail_even_if_security_passes():
    context = AgentContext(task="t")
    context.memory["test_passed"] = False
    context.memory["security_passed"] = True

    result = ReviewerAgent().run(context)

    assert result.success is False
    assert context.memory["review_decision"] == "changes_requested"
    assert "tests failing" in result.output


def test_rejects_when_security_fails_even_if_tests_pass():
    """This is the key new behaviour: passing tests alone is no longer
    enough to get approved if the Security Auditor found a HIGH issue."""
    context = AgentContext(task="t")
    context.memory["test_passed"] = True
    context.memory["security_passed"] = False

    result = ReviewerAgent().run(context)

    assert result.success is False
    assert context.memory["review_decision"] == "changes_requested"
    assert "security" in result.output.lower()


def test_security_passed_defaults_to_true_when_absent():
    """A workflow that never ran the security step shouldn't be auto-rejected."""
    context = AgentContext(task="t")
    context.memory["test_passed"] = True

    result = ReviewerAgent().run(context)

    assert result.success is True
    assert context.memory["review_decision"] == "approved"