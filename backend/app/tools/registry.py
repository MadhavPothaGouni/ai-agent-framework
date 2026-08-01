"""Plugin registry for tools.

Agents shouldn't need to `import app.tools.filesystem` and
`import app.tools.bash` by name forever — that means every new tool
requires touching core agent code. Instead, any BaseTool subclass can
opt into being discoverable simply by decorating itself:

    from app.tools.registry import register_tool
    from app.tools.base import BaseTool, ToolResult

    @register_tool
    class MyThirdPartyTool(BaseTool):
        name = "my_tool"
        description = "..."

        def run(self, **kwargs) -> ToolResult:
            ...

Once that module has been imported anywhere, `app.tools.registry.get_registry()
.create("my_tool", **kwargs)` can instantiate it — no changes to this
file, and no changes to the agents that merely look tools up by name.
That's what makes this a plugin system rather than a fixed toolbox.
"""
from typing import Type

from app.tools.base import BaseTool


class ToolRegistry:
    """Maps tool name -> BaseTool subclass, with factory-style construction.

    Tools are registered as classes, not instances, because most tools
    (FileSystemTool, BashTool, ...) need per-workflow-run constructor
    arguments (a sandboxed root directory, a cwd, a timeout, ...). The
    registry's job is discovery + construction, not lifecycle.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Type[BaseTool]] = {}

    def register(self, tool_cls: Type[BaseTool]) -> Type[BaseTool]:
        name = getattr(tool_cls, "name", "") or ""
        if not name or name == "base_tool":
            raise ValueError(
                f"{tool_cls.__name__} must define a real 'name' class attribute before registering"
            )
        if name in self._tools and self._tools[name] is not tool_cls:
            raise ValueError(
                f"A different tool is already registered under the name '{name}': "
                f"{self._tools[name].__name__}"
            )
        self._tools[name] = tool_cls
        return tool_cls

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Type[BaseTool]:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(
                f"No tool registered under '{name}'. Known tools: {self.names()}"
            ) from exc

    def create(self, name: str, **kwargs) -> BaseTool:
        """Look up a tool class by name and instantiate it with kwargs."""
        return self.get(name)(**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> dict[str, str]:
        return {name: cls.description for name, cls in sorted(self._tools.items())}


# A single process-wide registry — mirrors how app.core.providers.get_provider()
# and app.core.rate_limit's module-level limiter list work elsewhere in this
# codebase: one shared instance, imported wherever it's needed.
_registry = ToolRegistry()


def register_tool(tool_cls: Type[BaseTool]) -> Type[BaseTool]:
    """Class decorator: registers a BaseTool subclass under its `name`."""
    return _registry.register(tool_cls)


def get_registry() -> ToolRegistry:
    return _registry