from app.agents.base import AgentContext, AgentResult, BaseAgent


class ReviewerAgent(BaseAgent):
    name = "reviewer"

    def run(self, context: AgentContext) -> AgentResult:
        passed = context.memory.get("test_passed", False)
        decision = "approved" if passed else "changes_requested"

        context.memory["review_decision"] = decision
        summary = f"Review decision: {decision}."

        return AgentResult(output=summary, success=passed, metadata={"decision": decision})