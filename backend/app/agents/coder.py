
from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.code_extraction import extract_code_block
from app.core.providers import get_provider
from app.core.providers.base import LLMProvider
from app.tools import get_registry

SOLUTION_FILENAME = "solution.py"


class CoderAgent(BaseAgent):
    name = "coder"

    def __init__(self, provider: LLMProvider | None = None) -> None:
        # Injectable so tests can supply a fake provider instead of hitting
        # a real API; defaults to whatever LLM_PROVIDER is configured.
        self._provider = provider

    def run(self, context: AgentContext) -> AgentResult:
        provider = self._provider or get_provider()
        plan = context.memory.get("plan", context.task)
        previous_failure = context.memory.get("previous_failure")

        prompt = (
            f"You are a coding agent. Implement the following plan:\n{plan}\n\n"
            "Return ONLY the complete Python source code for the solution — "
            "no markdown formatting, no explanations, just the code."
        )
        if previous_failure:
            prompt += f"\n\nThe previous attempt failed review with:\n{previous_failure}\nFix it."

        raw = provider.complete([{"role": "user", "content": prompt}])
        code = extract_code_block(raw)
        context.memory["code"] = code

        metadata: dict = {"provider": provider.name}

        workspace_dir = context.memory.get("workspace_dir")
        if workspace_dir:
            fs = get_registry().create("filesystem", root=workspace_dir)
            write_result = fs.run(action="write", path=SOLUTION_FILENAME, content=code)
            metadata["file_written"] = write_result.success
            metadata["file_path"] = f"{workspace_dir}/{SOLUTION_FILENAME}"

        return AgentResult(output=code, success=True, metadata=metadata)