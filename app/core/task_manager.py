from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.state_manager import StateManager


class TaskManager:
    """Create, track, update, and complete AI development tasks."""

    VALID_STATUSES = {
        "pending",
        "in_progress",
        "testing",
        "review",
        "done",
        "rework",
        "blocked",
    }

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp."""

        return datetime.now(timezone.utc).isoformat()

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        assigned_to: str | None = None,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a new task."""

        tasks = self.state_manager.load_tasks()

        task = {
            "id": f"TASK-{uuid4().hex[:8].upper()}",
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "assigned_to": assigned_to,
            "dependencies": dependencies or [],
            "iteration": 0,
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": self._now(),
            "updated_at": self._now(),
        }

        tasks.append(task)
        self.state_manager.save_tasks(tasks)

        return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Return a task by ID."""

        tasks = self.state_manager.load_tasks()

        for task in tasks:
            if task["id"] == task_id:
                return task

        return None

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return all tasks."""

        return self.state_manager.load_tasks()

    def assign_task(self, task_id: str, agent_name: str) -> dict[str, Any]:
        """Assign a task to an agent."""

        task = self._require_task(task_id)

        task["assigned_to"] = agent_name

        if task["status"] == "pending":
            task["status"] = "in_progress"

        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        """Update the status of a task."""

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid task status: {status}. "
                f"Valid statuses: {sorted(self.VALID_STATUSES)}"
            )

        task = self._require_task(task_id)

        task["status"] = status
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def update_progress(self, task_id: str, progress: int) -> dict[str, Any]:
        """Update task progress from 0 to 100."""

        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100.")

        task = self._require_task(task_id)

        task["progress"] = progress
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def start_new_iteration(self, task_id: str) -> dict[str, Any]:
        """Increment the task iteration and mark it for rework."""

        task = self._require_task(task_id)

        task["iteration"] += 1
        task["status"] = "in_progress"
        task["error"] = None
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def record_result(
        self,
        task_id: str,
        result: str,
        progress: int = 100,
    ) -> dict[str, Any]:
        """Record the result of a task execution."""

        task = self._require_task(task_id)

        task["result"] = result
        task["progress"] = progress
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def record_error(self, task_id: str, error: str) -> dict[str, Any]:
        """Record an error and mark the task for rework."""

        task = self._require_task(task_id)

        task["error"] = error
        task["status"] = "rework"
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def complete_task(self, task_id: str, result: str) -> dict[str, Any]:
        """Mark a task as completed."""

        task = self._require_task(task_id)

        task["status"] = "done"
        task["progress"] = 100
        task["result"] = result
        task["error"] = None
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def block_task(self, task_id: str, reason: str) -> dict[str, Any]:
        """Mark a task as blocked."""

        task = self._require_task(task_id)

        task["status"] = "blocked"
        task["error"] = reason
        task["updated_at"] = self._now()

        self._save_updated_task(task)

        return task

    def _require_task(self, task_id: str) -> dict[str, Any]:
        """Return a task or raise an informative error."""

        task = self.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        return task

    def _save_updated_task(self, updated_task: dict[str, Any]) -> None:
        """Replace an existing task and persist the task list."""

        tasks = self.state_manager.load_tasks()

        for index, task in enumerate(tasks):
            if task["id"] == updated_task["id"]:
                tasks[index] = updated_task
                self.state_manager.save_tasks(tasks)
                return

        raise ValueError(
            f"Could not save task because it was not found: "
            f"{updated_task['id']}"
        )