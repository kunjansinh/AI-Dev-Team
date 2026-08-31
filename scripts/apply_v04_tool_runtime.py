from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Add the workspace tool registry.
registry = ROOT / "app/tools/workspace_registry.py"
registry.write_text('''from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom app.core.permissions import PermissionManager\nfrom app.core.tool_manager import ToolManager\nfrom app.tools.filesystem import FilesystemTool\nfrom app.tools.git import GitTool\nfrom app.tools.terminal import TerminalTool\nfrom app.tools.testing import TestingTool\n\n\ndef create_workspace_tool_manager(\n    workspace: str | Path,\n    permission_manager: PermissionManager | None = None,\n) -> ToolManager:\n    """Create one permission-aware tool gateway for a workspace."""\n\n    workspace_path = Path(workspace).resolve()\n    filesystem = FilesystemTool(workspace_path)\n    terminal = TerminalTool(workspace_path)\n    git = GitTool(workspace_path)\n    testing = TestingTool()\n\n    manager = ToolManager(permission_manager=permission_manager)\n\n    manager.register("read_file", "Read a UTF-8 text file inside the workspace.", filesystem.read_file)\n    manager.register("list_files", "List files contained in the workspace.", filesystem.list_files)\n    manager.register("create_file", "Create a new text file inside the workspace.", _create_file(filesystem))\n    manager.register("modify_file", "Modify an existing text file inside the workspace.", _modify_file(filesystem))\n    manager.register("run_tests", "Run the workspace pytest suite and return structured evidence.", lambda: testing.run_pytest(workspace_path))\n    manager.register("git_status", "Inspect the workspace Git status.", git.status)\n    manager.register("git_diff", "Inspect the workspace Git diff.", git.diff)\n    manager.register("run_command", "Run an allow-listed command inside the workspace.", terminal.run)\n\n    return manager\n\n\ndef _create_file(filesystem: FilesystemTool):\n    def create_file(relative_path: str, content: str) -> str:\n        path = filesystem.safe_path(relative_path)\n        if path.exists():\n            raise FileExistsError(f"File already exists: {relative_path}")\n        return filesystem.write_file(relative_path, content)\n    return create_file\n\n\ndef _modify_file(filesystem: FilesystemTool):\n    def modify_file(relative_path: str, content: str) -> str:\n        path = filesystem.safe_path(relative_path)\n        if not path.exists():\n            raise FileNotFoundError(f"File does not exist: {relative_path}")\n        return filesystem.write_file(relative_path, content)\n    return modify_file\n''', encoding="utf-8")

# 2. Give the developer permission to use the already-hardened TerminalTool.
permissions = ROOT / "app/core/permissions.py"
patch_text(
    permissions,
    '            "git_diff",\n        },\n        "qa": {',
    '            "git_diff",\n            "run_command",\n        },\n        "qa": {',
)

# 3. Wire the registry into TeamRuntime.
runtime = ROOT / "app/runtime/team_runtime.py"
patch_text(
    runtime,
    'from app.tools.testing import TestingTool\n',
    'from app.tools.testing import TestingTool\nfrom app.tools.workspace_registry import create_workspace_tool_manager\n',
)
patch_text(
    runtime,
    '        self.agent_manager = AgentManager()\n\n        self.manager = ManagerAgent(',
    '        self.agent_manager = AgentManager()\n        self.tool_manager = create_workspace_tool_manager(\n            developer_workspace,\n        )\n\n        self.manager = ManagerAgent(',
)
patch_text(
    runtime,
    '            testing_tool=TestingTool(),\n        )',
    '            testing_tool=TestingTool(),\n            tool_manager=self.tool_manager,\n        )',
)

# 4. Make DeveloperAgent use the gateway for writes and tests when runtime provides it.
developer = ROOT / "app/agents/developer_agent.py"
patch_text(
    developer,
    'from app.agents.base_agent import BaseAgent\nfrom app.tools.testing import TestingTool\n',
    'from app.agents.base_agent import BaseAgent\nfrom app.core.tool_manager import ToolManager\nfrom app.tools.testing import TestingTool\n',
)
patch_text(
    developer,
    '        testing_tool: TestingTool | None = None,\n    ) -> None:',
    '        testing_tool: TestingTool | None = None,\n        tool_manager: ToolManager | None = None,\n    ) -> None:',
)
patch_text(
    developer,
    '        self.testing_tool = testing_tool or TestingTool()\n',
    '        self.testing_tool = testing_tool or TestingTool()\n        self.tool_manager = tool_manager\n',
)
patch_text(
    developer,
    '''                path = self._safe_workspace_path(\n                    relative_path\n                )\n\n                path.parent.mkdir(\n                    parents=True,\n                    exist_ok=True,\n                )\n\n                path.write_text(\n                    content,\n                    encoding="utf-8",\n                )\n\n                written_files.append(\n                    str(\n                        path.relative_to(\n                            self.workspace\n                        )\n                    )\n                )''',
    '''                written_files.append(\n                    self._write_generated_file(\n                        relative_path,\n                        content,\n                    )\n                )''',
)
patch_text(
    developer,
    '                validation = self.testing_tool.run_pytest(\n                    self.workspace\n                )',
    '                validation = self._run_validation()',
)
anchor = '    def _build_developer_prompt(\n'
helpers = '''    def _write_generated_file(\n        self,\n        relative_path: str,\n        content: str,\n    ) -> str:\n        """Write through the controlled tool gateway when configured."""\n\n        path = self._safe_workspace_path(relative_path)\n\n        if self.tool_manager is None:\n            path.parent.mkdir(parents=True, exist_ok=True)\n            path.write_text(content, encoding="utf-8")\n            return str(path.relative_to(self.workspace)).replace("\\\\", "/")\n\n        tool_name = "modify_file" if path.exists() else "create_file"\n        result = self.tool_manager.execute(\n            self.name,\n            tool_name,\n            relative_path=relative_path,\n            content=content,\n        )\n\n        if result["status"] != "success":\n            raise PermissionError(\n                result.get("error", "Tool execution failed.")\n            )\n\n        return str(result["result"])\n\n    def _run_validation(self) -> dict[str, Any]:\n        """Run pytest through the controlled tool gateway when configured."""\n\n        if self.tool_manager is None:\n            return self.testing_tool.run_pytest(self.workspace)\n\n        result = self.tool_manager.execute(\n            self.name,\n            "run_tests",\n        )\n\n        if result["status"] != "success":\n            raise RuntimeError(\n                result.get("error", "Test tool failed.")\n            )\n\n        return result["result"]\n\n'''
patch_text(developer, anchor, helpers + anchor)

# 5. Add focused integration tests.
test = ROOT / "tests/test_workspace_tool_registry.py"
test.write_text('''from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom app.tools.workspace_registry import create_workspace_tool_manager\n\n\ndef test_workspace_registry_registers_all_runtime_tools(tmp_path: Path) -> None:\n    manager = create_workspace_tool_manager(tmp_path / "workspace")\n    assert set(manager.list_tools()) == {\n        "read_file", "list_files", "create_file", "modify_file",\n        "run_tests", "git_status", "git_diff", "run_command",\n    }\n\n\ndef test_workspace_registry_uses_permissions(tmp_path: Path) -> None:\n    manager = create_workspace_tool_manager(tmp_path / "workspace")\n    assert manager.can_execute("developer", "create_file")\n    assert not manager.can_execute("researcher", "create_file")\n\n\ndef test_workspace_registry_routes_filesystem_operations(tmp_path: Path) -> None:\n    manager = create_workspace_tool_manager(tmp_path / "workspace")\n    created = manager.execute("developer", "create_file", relative_path="src/example.py", content="VALUE = 1\\n")\n    assert created["status"] == "success"\n    read = manager.execute("developer", "read_file", relative_path="src/example.py")\n    assert read["status"] == "success"\n    assert read["result"] == "VALUE = 1\\n"\n\n\ndef test_workspace_registry_blocks_unauthorized_file_write(tmp_path: Path) -> None:\n    manager = create_workspace_tool_manager(tmp_path / "workspace")\n    result = manager.execute("researcher", "create_file", relative_path="blocked.py", content="VALUE = 1\\n")\n    assert result["status"] == "error"\n    assert result["error_type"] == "PermissionError"\n    assert not (tmp_path / "workspace" / "blocked.py").exists()\n''', encoding="utf-8")

runtime_test = ROOT / "tests/test_team_runtime_tools.py"
runtime_test.write_text('''from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom app.core.state_manager import StateManager\nfrom app.core.task_manager import TaskManager\nfrom app.runtime.team_runtime import TeamRuntime\n\n\nclass FakeRouter:\n    def generate(self, prompt: str, task_type: str, think: bool = False) -> str:\n        return "unused"\n\n\ndef test_runtime_exposes_workspace_tool_manager(tmp_path: Path) -> None:\n    state = StateManager(tmp_path / "state")\n    tasks = TaskManager(state)\n    runtime = TeamRuntime(\n        state_manager=state,\n        task_manager=tasks,\n        router=FakeRouter(),\n        developer_workspace=str(tmp_path / "workspace"),\n    )\n    assert runtime.tool_manager.can_execute("developer", "create_file")\n    assert runtime.developer.tool_manager is runtime.tool_manager\n''', encoding="utf-8")

print("V0.4 tool runtime wiring applied.")
print("Next: python -m pytest -q")
