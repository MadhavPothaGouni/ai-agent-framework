"""Example third-party-style tool: an HTTP GET fetcher.

This isn't wired into any agent's core logic anywhere — it exists purely
to prove that the plugin system works: a brand-new tool can register
itself with `@register_tool` and immediately become discoverable via
`get_registry().create("http", ...)`, without editing app/tools/registry.py,
app/tools/base.py, or any agent. That's the actual test of "is this a
plugin system" — can code outside the core package add a capability.

SECURITY NOTE: only GET is supported (no arbitrary method/body), and
requests are capped by both a byte limit and a timeout, since — unlike
BashTool — the URL here could plausibly come from LLM-generated agent
output rather than a hardcoded command.
"""
import httpx

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import register_tool

_MAX_RESPONSE_BYTES = 200_000


@register_tool
class HttpTool(BaseTool):
    name = "http"
    description = "Fetch a URL over HTTP GET and return the response body (capped size, with a timeout)."

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, url: str) -> ToolResult:  # type: ignore[override]
        if not (url.startswith("http://") or url.startswith("https://")):
            return ToolResult(output="", success=False, error="Only http:// and https:// URLs are allowed")

        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            return ToolResult(output="", success=False, error=f"Request failed: {exc}")

        body = response.text[:_MAX_RESPONSE_BYTES]
        return ToolResult(
            output=body,
            success=response.is_success,
            error=None if response.is_success else f"HTTP {response.status_code}",
        )