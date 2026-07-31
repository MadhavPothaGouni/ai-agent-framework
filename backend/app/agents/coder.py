from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.providers import get_provider


class CoderAgent(BaseAgent):
    name = "coder"

    def run(self, context: AgentContext) -> AgentResult:
        provider = get_provider()
        plan = context.memory.get("plan", context.task)
        previous_failure = context.memory.get("previous_failure")

        prompt = f"You are a coding agent. Implement the following plan:\n{plan}"
        if previous_failure:
            prompt += f"\n\nThe previous attempt failed review with: {previous_failure}\nFix it."

        code = provider.complete([{"role": "user", "content": prompt}])
        context.memory["code"] = code

        return AgentResult(output=code, success=True, metadata={"provider": provider.name})