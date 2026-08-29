from __future__ import annotations

from pathlib import Path

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.runtime.team_runtime import TeamRuntime


class FakeRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt: str, task_type: str, think: bool = False) -> str:
        self.calls.append((task_type, prompt, think))
        return "unused"


def build_runtime(tmp_path: Path) -> TeamRuntime:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    return TeamRuntime(
        state_manager=state,
        task_manager=tasks,
        router=FakeRouter(),
        developer_workspace=str(tmp_path / "workspace"),
    )


def test_runtime_registers_complete_team(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    assert set(runtime.agent_manager.list_agents()) == {
        "developer",
        "architect",
        "researcher",
        "qa",
        "security",
    }

    description = runtime.describe_team()
    assert "coding" in description["developer"]
    assert "architecture" in description["architect"]
    assert "research" in description["researcher"]
    assert "testing" in description["qa"]
    assert "security" in description["security"]


def test_runtime_routes_manager_and_specialists(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)

    assert runtime.manager.llm_client.task_type == "management"
    assert runtime.developer.llm_client.task_type == "coding"
    assert runtime.specialists["architect"].llm_client.task_type == "architecture"
    assert runtime.specialists["researcher"].llm_client.task_type == "research"
    assert runtime.specialists["qa"].llm_client.task_type == "qa"
    assert runtime.specialists["security"].llm_client.task_type == "security"
