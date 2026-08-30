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


def test_terminal_tool_allows_approved_commands(tmp_path: Path) -> None:
    tool = TerminalTool(tmp_path / "workspace")

    result = tool.run(
        ["python", "-c", "print('approved')"]
    )

    assert result["exit_code"] == 0
    assert "approved" in result["stdout"]


def test_terminal_tool_rejects_unapproved_commands(tmp_path: Path) -> None:
    tool = TerminalTool(tmp_path / "workspace")

    try:
        tool.run(["powershell", "-Command", "Write-Output blocked"])
    except PermissionError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError(
            "Unapproved command was executed."
        )


def test_terminal_tool_supports_custom_allowlist(tmp_path: Path) -> None:
    tool = TerminalTool(
        tmp_path / "workspace",
        allowed_commands={"custom"},
    )

    assert "custom" in tool.allowed_commands
    assert "python" not in tool.allowed_commands
