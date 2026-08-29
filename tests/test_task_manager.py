from pathlib import Path

import pytest

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


@pytest.fixture
def task_manager(tmp_path: Path) -> TaskManager:
    state_manager = StateManager(tmp_path / "state")
    return TaskManager(state_manager)


def test_create_task(task_manager: TaskManager) -> None:
    task = task_manager.create_task(
        title="Build authentication",
        description="Implement user authentication.",
        priority="high",
    )

    assert task["id"].startswith("TASK-")
    assert task["title"] == "Build authentication"
    assert task["status"] == "pending"
    assert task["priority"] == "high"
    assert task["iteration"] == 0
    assert task["progress"] == 0


def test_assign_task_moves_pending_task_to_in_progress(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Build API")

    updated = task_manager.assign_task(task["id"], "developer")

    assert updated["assigned_to"] == "developer"
    assert updated["status"] == "in_progress"


def test_progress_and_status_can_be_updated(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Build frontend")

    task_manager.update_progress(task["id"], 60)
    task_manager.update_status(task["id"], "testing")

    updated = task_manager.get_task(task["id"])

    assert updated is not None
    assert updated["progress"] == 60
    assert updated["status"] == "testing"


def test_failed_task_enters_rework(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Implement login")

    updated = task_manager.record_error(
        task["id"],
        "Authentication test failed.",
    )

    assert updated["status"] == "rework"
    assert updated["error"] == "Authentication test failed."


def test_new_iteration_resets_task_to_in_progress(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Fix authentication")

    task_manager.record_error(task["id"], "Test failed.")
    updated = task_manager.start_new_iteration(task["id"])

    assert updated["iteration"] == 1
    assert updated["status"] == "in_progress"
    assert updated["error"] is None


def test_task_can_be_completed(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Complete API")

    updated = task_manager.complete_task(
        task["id"],
        "API implementation and tests completed.",
    )

    assert updated["status"] == "done"
    assert updated["progress"] == 100
    assert updated["result"] == (
        "API implementation and tests completed."
    )


def test_blocked_task_is_recorded(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Deploy system")

    updated = task_manager.block_task(
        task["id"],
        "Deployment credentials are unavailable.",
    )

    assert updated["status"] == "blocked"
    assert updated["error"] == (
        "Deployment credentials are unavailable."
    )


def test_invalid_status_is_rejected(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Test validation")

    with pytest.raises(ValueError):
        task_manager.update_status(task["id"], "banana")


def test_invalid_progress_is_rejected(
    task_manager: TaskManager,
) -> None:
    task = task_manager.create_task("Test validation")

    with pytest.raises(ValueError):
        task_manager.update_progress(task["id"], 150)


def test_missing_task_returns_none(
    task_manager: TaskManager,
) -> None:
    result = task_manager.get_task("TASK-NOT-REAL")

    assert result is None

def test_missing_task_rejects_update(
    task_manager: TaskManager,
) -> None:
    with pytest.raises(ValueError, match="Task not found"):
        task_manager.update_status(
            "TASK-NOT-REAL",
            "in_progress",
        )