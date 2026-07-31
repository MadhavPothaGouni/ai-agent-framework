import tempfile
from pathlib import Path

from app.tools.bash import BashTool
from app.tools.filesystem import FileSystemTool


def test_filesystem_write_then_read_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        fs = FileSystemTool(root=tmp)
        write_result = fs.run(action="write", path="hello.txt", content="hi there")
        assert write_result.success

        read_result = fs.run(action="read", path="hello.txt")
        assert read_result.success
        assert read_result.output == "hi there"


def test_filesystem_list_shows_written_files():
    with tempfile.TemporaryDirectory() as tmp:
        fs = FileSystemTool(root=tmp)
        fs.run(action="write", path="a.txt", content="a")
        fs.run(action="write", path="b.txt", content="b")

        result = fs.run(action="list")
        assert result.success
        assert set(result.output.splitlines()) == {"a.txt", "b.txt"}


def test_filesystem_blocks_path_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        fs = FileSystemTool(root=tmp)
        result = fs.run(action="write", path="../escape.txt", content="nope")
        assert result.success is False
        assert "escapes" in result.error


def test_filesystem_unknown_action_fails_cleanly():
    with tempfile.TemporaryDirectory() as tmp:
        fs = FileSystemTool(root=tmp)
        result = fs.run(action="delete", path="whatever.txt")
        assert result.success is False
        assert "Unknown action" in result.error


def test_bash_runs_command_in_given_cwd():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "marker.txt").write_text("present", encoding="utf-8")
        bash = BashTool(cwd=tmp)

        result = bash.run("python -c \"import pathlib; print(pathlib.Path('marker.txt').exists())\"")
        assert result.success
        assert "True" in result.output


def test_bash_reports_failure_on_nonzero_exit():
    with tempfile.TemporaryDirectory() as tmp:
        bash = BashTool(cwd=tmp)
        result = bash.run("python -c \"import sys; sys.exit(1)\"")
        assert result.success is False