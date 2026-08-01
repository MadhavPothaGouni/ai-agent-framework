
import pytest

from app.tools import get_registry  # importing app.tools registers built-ins
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, register_tool


def test_builtin_tools_are_registered_on_import():
    registry = get_registry()
    assert "filesystem" in registry.names()
    assert "bash" in registry.names()
    assert "http" in registry.names()


def test_get_registry_returns_the_same_shared_instance():
    assert get_registry() is get_registry()


def test_create_instantiates_the_registered_class(tmp_path):
    fs = get_registry().create("filesystem", root=tmp_path)
    from app.tools.filesystem import FileSystemTool

    assert isinstance(fs, FileSystemTool)


def test_get_unknown_tool_raises_with_helpful_message():
    registry = get_registry()
    with pytest.raises(KeyError, match="No tool registered under 'nope'"):
        registry.get("nope")


def test_describe_includes_each_tool_description():
    descriptions = get_registry().describe()
    assert "filesystem" in descriptions
    assert descriptions["filesystem"]  # non-empty description string


# ---------------------------------------------------------------------------
# A standalone registry (not the shared singleton) to test registration
# rules in isolation, without mutating global state other tests rely on.
# ---------------------------------------------------------------------------


def test_register_rejects_tool_without_a_real_name():
    registry = ToolRegistry()

    class UnnamedTool(BaseTool):
        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output="")

    with pytest.raises(ValueError, match="must define a real 'name'"):
        registry.register(UnnamedTool)


def test_register_rejects_name_collision_with_a_different_class():
    registry = ToolRegistry()

    class ToolA(BaseTool):
        name = "dup"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output="a")

    class ToolB(BaseTool):
        name = "dup"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output="b")

    registry.register(ToolA)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ToolB)


def test_register_same_class_twice_is_a_harmless_noop():
    registry = ToolRegistry()

    class ToolA(BaseTool):
        name = "idempotent"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output="a")

    registry.register(ToolA)
    registry.register(ToolA)  # should not raise
    assert registry.names() == ["idempotent"]


def test_unregister_removes_the_tool():
    registry = ToolRegistry()

    class ToolA(BaseTool):
        name = "temp"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(output="a")

    registry.register(ToolA)
    assert "temp" in registry.names()
    registry.unregister("temp")
    assert "temp" not in registry.names()
    registry.unregister("temp")  # unregistering something absent shouldn't raise


def test_third_party_style_tool_self_registers_via_decorator():
    """Proves the actual plugin claim: a tool defined completely outside
    app/tools/, with no edits to registry.py or any agent, becomes
    discoverable purely by being decorated and imported.
    """
    registry = get_registry()

    @register_tool
    class EchoPluginTool(BaseTool):
        name = "echo_plugin_test_tool"
        description = "Echoes back whatever text it's given."

        def __init__(self, prefix: str = "") -> None:
            self.prefix = prefix

        def run(self, text: str = "") -> ToolResult:  # type: ignore[override]
            return ToolResult(output=f"{self.prefix}{text}")

    try:
        assert "echo_plugin_test_tool" in registry.names()
        tool = registry.create("echo_plugin_test_tool", prefix=">> ")
        result = tool.run(text="hello")
        assert result.success is True
        assert result.output == ">> hello"
    finally:
        registry.unregister("echo_plugin_test_tool")


# ---------------------------------------------------------------------------
# HttpTool — network calls are faked so this suite stays hermetic/offline.
# ---------------------------------------------------------------------------


def test_http_tool_rejects_non_http_urls():
    from app.tools.http_tool import HttpTool

    tool = HttpTool()
    result = tool.run(url="ftp://example.com/file")
    assert result.success is False
    assert "http://" in result.error


def test_http_tool_returns_body_on_success(monkeypatch):
    import httpx

    from app.tools.http_tool import HttpTool

    class FakeResponse:
        text = "hello world"
        is_success = True
        status_code = 200

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    tool = HttpTool()
    result = tool.run(url="https://example.com")
    assert result.success is True
    assert result.output == "hello world"


def test_http_tool_wraps_request_errors(monkeypatch):
    import httpx

    from app.tools.http_tool import HttpTool

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "Client", FakeClient)

    tool = HttpTool()
    result = tool.run(url="https://example.com")
    assert result.success is False
    assert "Request failed" in result.error