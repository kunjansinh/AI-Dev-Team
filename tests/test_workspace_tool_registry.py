from __future__ import annotations

from pathlib import Path

from app.tools.workspace_registry import create_workspace_tool_manager


def test_workspace_registry_registers_all_runtime_tools(tmp_path: Path) -> None:
    manager = create_workspace_tool_manager(tmp_path / "workspace")
    assert set(manager.list_tools()) == {
        "read_file", "list_files", "create_file", "modify_file",
        "run_tests", "git_status", "git_diff", "run_command",
    }


def test_workspace_registry_uses_permissions(tmp_path: Path) -> None:
    manager = create_workspace_tool_manager(tmp_path / "workspace")
    assert manager.can_execute("developer", "create_file")
    assert not manager.can_execute("researcher", "create_file")


def test_workspace_registry_routes_filesystem_operations(tmp_path: Path) -> None:
    manager = create_workspace_tool_manager(tmp_path / "workspace")
    created = manager.execute("developer", "create_file", relative_path="src/example.py", content="VALUE = 1\n")
    assert created["status"] == "success"
    read = manager.execute("developer", "read_file", relative_path="src/example.py")
    assert read["status"] == "success"
    assert read["result"] == "VALUE = 1\n"


def test_workspace_registry_blocks_unauthorized_file_write(tmp_path: Path) -> None:
    manager = create_workspace_tool_manager(tmp_path / "workspace")
    result = manager.execute("researcher", "create_file", relative_path="blocked.py", content="VALUE = 1\n")
    assert result["status"] == "error"
    assert result["error_type"] == "PermissionError"
    assert not (tmp_path / "workspace" / "blocked.py").exists()
