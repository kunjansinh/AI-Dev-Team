from pathlib import Path

from app.tools.filesystem import FilesystemTool
from app.tools.terminal import TerminalTool


def test_filesystem_tool_is_workspace_safe(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path / "workspace")
    assert tool.write_file("src/example.py", "VALUE = 1\n") == "src/example.py"
    assert tool.read_file("src/example.py") == "VALUE = 1\n"
    assert "src/example.py" in tool.list_files()


def test_filesystem_tool_rejects_escape(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path / "workspace")
    try:
        tool.safe_path("../outside.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("Workspace escape was not rejected.")


def test_terminal_tool_runs_inside_workspace(tmp_path: Path) -> None:
    tool = TerminalTool(tmp_path / "workspace")
    result = tool.run(["python", "-c", "print('team-tool-ok')"])
    assert result["exit_code"] == 0
    assert "team-tool-ok" in result["stdout"]
