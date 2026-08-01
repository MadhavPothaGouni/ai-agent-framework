
import subprocess
from pathlib import Path

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import register_tool


@register_tool
class BashTool(BaseTool):
    name = "bash"
    description = "Run a shell command with its cwd restricted to the sandboxed workspace."

    def __init__(self, cwd: str | Path, timeout_seconds: int = 30) -> None:
        self.cwd = Path(cwd).resolve()
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds

    def run(self, command: str) -> ToolResult:  # type: ignore[override]
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            return ToolResult(output=proc.stdout + proc.stderr, success=proc.returncode == 0)
        except subprocess.TimeoutExpired:
            return ToolResult(
                output="", success=False, error=f"Command timed out after {self.timeout_seconds}s"
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output="", success=False, error=str(exc))