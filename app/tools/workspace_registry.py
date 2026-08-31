from __future__ import annotations

from pathlib import Path

from app.core.permissions import PermissionManager
from app.core.tool_manager import ToolManager
from app.tools.filesystem import FilesystemTool
from app.tools.git import GitTool
from app.tools.terminal import TerminalTool
from app.tools.testing import TestingTool


def create_workspace_tool_manager(
    workspace: str | Path,
    permission_manager: PermissionManager | None = None,
) -> ToolManager:
    """Create one permission-aware tool gateway for a workspace."""

    workspace_path = Path(workspace).resolve()
    filesystem = FilesystemTool(workspace_path)
    terminal = TerminalTool(workspace_path)
    git = GitTool(workspace_path)
    testing = TestingTool()

    manager = ToolManager(permission_manager=permission_manager)

    manager.register("read_file", "Read a UTF-8 text file inside the workspace.", filesystem.read_file)
    manager.register("list_files", "List files contained in the workspace.", filesystem.list_files)
    manager.register("create_file", "Create a new text file inside the workspace.", _create_file(filesystem))
    manager.register("modify_file", "Modify an existing text file inside the workspace.", _modify_file(filesystem))
    manager.register("run_tests", "Run the workspace pytest suite and return structured evidence.", lambda: testing.run_pytest(workspace_path))
    manager.register("git_status", "Inspect the workspace Git status.", git.status)
    manager.register("git_diff", "Inspect the workspace Git diff.", git.diff)
    manager.register("run_command", "Run an allow-listed command inside the workspace.", terminal.run)

    return manager


def _create_file(filesystem: FilesystemTool):
    def create_file(relative_path: str, content: str) -> str:
        path = filesystem.safe_path(relative_path)
        if path.exists():
            raise FileExistsError(f"File already exists: {relative_path}")
        return filesystem.write_file(relative_path, content)
    return create_file


def _modify_file(filesystem: FilesystemTool):
    def modify_file(relative_path: str, content: str) -> str:
        path = filesystem.safe_path(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {relative_path}")
        return filesystem.write_file(relative_path, content)
    return modify_file
