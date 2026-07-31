"""Base Tool abstraction for tool-calling agents (git, bash, fs, http, ...)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    output: str
    success: bool = True
    error: str | None = None


class BaseTool(ABC):
    """Common interface every tool (Git, Docker, Bash, FileSystem, ...) implements."""

    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError
