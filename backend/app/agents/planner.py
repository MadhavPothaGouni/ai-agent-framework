from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.providers import get_provider


class PlannerAgent(BaseAgent):
    name = "planner"

    def run(self, context: AgentContext) -> AgentResult:
        provider = get_provider()
        reply = provider.complete(context.history)
        return AgentResult(
            output=reply,
            success=True,
            metadata={"provider": provider.name, "turn": len(context.history)},
        )