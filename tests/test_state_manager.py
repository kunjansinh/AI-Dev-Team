from pathlib import Path

from app.core.state_manager import StateManager


def test_state_manager_creates_default_state(tmp_path: Path) -> None:
    state_manager = StateManager(tmp_path / "state")

    state = state_manager.load_project_state()

    assert state["project_name"] == "AI-Dev-Team"
    assert state["status"] == "initializing"
    assert state["current_phase"] == "state_management"


def test_project_state_can_be_updated(tmp_path: Path) -> None:
    state_manager = StateManager(tmp_path / "state")

    updated_state = state_manager.update_project_state(
        status="in_progress",
        current_task="TASK-001",
    )

    assert updated_state["status"] == "in_progress"
    assert updated_state["current_task"] == "TASK-001"

    reloaded_state = state_manager.load_project_state()

    assert reloaded_state["status"] == "in_progress"
    assert reloaded_state["current_task"] == "TASK-001"


def test_checkpoint_can_be_saved_and_loaded(tmp_path: Path) -> None:
    state_manager = StateManager(tmp_path / "state")

    checkpoint = {
        "task_id": "TASK-001",
        "status": "in_progress",
        "iteration": 1,
        "next_action": "Build task manager",
    }

    checkpoint_path = state_manager.create_checkpoint(
        "TASK-001",
        checkpoint,
    )

    assert checkpoint_path.exists()

    loaded_checkpoint = state_manager.load_checkpoint("TASK-001")

    assert loaded_checkpoint == checkpoint


def test_missing_checkpoint_returns_none(tmp_path: Path) -> None:
    state_manager = StateManager(tmp_path / "state")

    result = state_manager.load_checkpoint("TASK-999")

    assert result is None