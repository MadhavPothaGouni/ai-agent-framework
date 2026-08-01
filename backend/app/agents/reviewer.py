
from app.agents.base import AgentContext, AgentResult, BaseAgent


class ReviewerAgent(BaseAgent):
    name = "reviewer"

    def run(self, context: AgentContext) -> AgentResult:
        tests_passed = context.memory.get("test_passed", False)
        security_passed = context.memory.get("security_passed", True)
        passed = tests_passed and security_passed

        if passed:
            decision = "approved"
            reason = None
        elif not tests_passed:
            decision = "changes_requested"
            reason = "tests failing"
        else:
            decision = "changes_requested"
            reason = "unresolved security findings"

        context.memory["review_decision"] = decision
        summary = f"Review decision: {decision}."
        if reason:
            summary += f" Reason: {reason}."

        return AgentResult(
            output=summary,
            success=passed,
            metadata={"decision": decision, "tests_passed": tests_passed, "security_passed": security_passed},
        )