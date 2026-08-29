from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateManager:
    """Manage persistent JSON state for the AI development team."""

    def __init__(self, state_directory: str | Path = "data/state"):
        self.state_directory = Path(state_directory)
        self.state_directory.mkdir(parents=True, exist_ok=True)

        self.project_state_file = self.state_directory / "project_state.json"
        self.tasks_file = self.state_directory / "tasks.json"
        self.decisions_file = self.state_directory / "decisions.json"
        self.agents_file = self.state_directory / "agents.json"

        self._initialize_files()

    def _initialize_files(self) -> None:
        """Create state files with safe default values if they do not exist."""

        defaults = {
            self.project_state_file: {
                "project_name": "AI-Dev-Team",
                "status": "initializing",
                "current_phase": "state_management",
                "current_task": None,
            },
            self.tasks_file: [],
            self.decisions_file: [],
            self.agents_file: {},
        }

        for file_path, default_value in defaults.items():
            if not file_path.exists():
                self._write_json(file_path, default_value)

    def _read_json(self, file_path: Path) -> Any:
        """Read JSON data from a file."""

        try:
            with file_path.open("r", encoding="utf-8") as file:
                return json.load(file)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in state file: {file_path}"
            ) from exc

    def _write_json(self, file_path: Path, data: Any) -> None:
        """Write JSON data to a file."""

        temporary_file = file_path.with_suffix(file_path.suffix + ".tmp")

        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
            file.write("\n")

        temporary_file.replace(file_path)

    def load_project_state(self) -> dict[str, Any]:
        """Load the main project state."""

        return self._read_json(self.project_state_file)

    def save_project_state(self, state: dict[str, Any]) -> None:
        """Save the main project state."""

        self._write_json(self.project_state_file, state)

    def update_project_state(self, **updates: Any) -> dict[str, Any]:
        """Update selected project-state fields and save them."""

        state = self.load_project_state()
        state.update(updates)
        self.save_project_state(state)

        return state

    def load_tasks(self) -> list[dict[str, Any]]:
        """Load all tasks."""

        return self._read_json(self.tasks_file)

    def save_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Save all tasks."""

        self._write_json(self.tasks_file, tasks)

    def load_decisions(self) -> list[dict[str, Any]]:
        """Load project decisions."""

        return self._read_json(self.decisions_file)

    def save_decisions(self, decisions: list[dict[str, Any]]) -> None:
        """Save project decisions."""

        self._write_json(self.decisions_file, decisions)

    def load_agents(self) -> dict[str, Any]:
        """Load agent states."""

        return self._read_json(self.agents_file)

    def save_agents(self, agents: dict[str, Any]) -> None:
        """Save agent states."""

        self._write_json(self.agents_file, agents)

    def create_checkpoint(
        self,
        task_id: str,
        checkpoint_data: dict[str, Any],
    ) -> Path:
        """Save a checkpoint for a task."""

        checkpoints_directory = self.state_directory.parent / "checkpoints"
        checkpoints_directory.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoints_directory / f"{task_id}.json"

        self._write_json(checkpoint_file, checkpoint_data)

        return checkpoint_file

    def load_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Load a task checkpoint if one exists."""

        checkpoints_directory = self.state_directory.parent / "checkpoints"
        checkpoint_file = checkpoints_directory / f"{task_id}.json"

        if not checkpoint_file.exists():
            return None

        return self._read_json(checkpoint_file)