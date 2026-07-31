from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.providers import get_provider
from app.tools.filesystem import FileSystemTool

SOLUTION_FILENAME = "solution.py"


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

        metadata: dict = {"provider": provider.name}

        workspace_dir = context.memory.get("workspace_dir")
        if workspace_dir:
            fs = FileSystemTool(root=workspace_dir)
            write_result = fs.run(action="write", path=SOLUTION_FILENAME, content=code)
            metadata["file_written"] = write_result.success
            metadata["file_path"] = f"{workspace_dir}/{SOLUTION_FILENAME}"

        return AgentResult(output=code, success=True, metadata=metadata)