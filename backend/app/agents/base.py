"""Base Agent abstraction.

Every agent (Planner, Coder, Tester, Reviewer, ...) implements this
interface so the orchestrator can chain them without caring about
what's underneath.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Shared state passed between agents in a workflow run."""

    task: str
    history: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    output: str
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Common interface for all agents in the framework."""

    name: str = "base_agent"

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's step given the shared context, and return a result."""
        raise NotImplementedError
