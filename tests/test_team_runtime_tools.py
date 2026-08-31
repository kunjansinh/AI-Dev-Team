from __future__ import annotations

from pathlib import Path

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.runtime.team_runtime import TeamRuntime


class FakeRouter:
    def generate(self, prompt: str, task_type: str, think: bool = False) -> str:
        return "unused"


def test_runtime_exposes_workspace_tool_manager(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    runtime = TeamRuntime(
        state_manager=state,
        task_manager=tasks,
        router=FakeRouter(),
        developer_workspace=str(tmp_path / "workspace"),
    )
    assert runtime.tool_manager.can_execute("developer", "create_file")
    assert runtime.developer.tool_manager is runtime.tool_manager
