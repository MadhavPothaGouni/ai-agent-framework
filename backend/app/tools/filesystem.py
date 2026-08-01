
from pathlib import Path

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import register_tool


@register_tool
class FileSystemTool(BaseTool):
    name = "filesystem"
    description = "Read, write, and list files inside a sandboxed workspace directory."

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError(f"Path '{relative_path}' escapes the sandboxed workspace")
        return target

    def run(self, action: str, path: str = "", content: str = "") -> ToolResult:  # type: ignore[override]
        try:
            if action == "write":
                target = self._resolve(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(output=f"Wrote {len(content)} bytes to {path}")

            if action == "read":
                target = self._resolve(path)
                return ToolResult(output=target.read_text(encoding="utf-8"))

            if action == "list":
                target = self._resolve(path or ".")
                names = sorted(p.name for p in target.iterdir())
                return ToolResult(output="\n".join(names))

            return ToolResult(output="", success=False, error=f"Unknown action: {action}")
        except Exception as exc:  # noqa: BLE001 — surface any failure as a ToolResult, don't crash the agent
            return ToolResult(output="", success=False, error=str(exc))