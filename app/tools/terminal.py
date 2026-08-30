from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


class TerminalTool:
    """Run approved commands inside a workspace."""

    DEFAULT_ALLOWED_COMMANDS = {
        "python",
        "python3",
        "pytest",
        "git",
    }

    def __init__(
        self,
        workspace: str | Path,
        allowed_commands: set[str] | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.allowed_commands = (
            set(allowed_commands)
            if allowed_commands is not None
            else set(self.DEFAULT_ALLOWED_COMMANDS)
        )

    def run(
        self,
        command: Sequence[str],
        timeout: int = 120,
    ) -> dict:
        if not command:
            raise ValueError("Command cannot be empty.")

        executable = Path(command[0]).name.lower()

        if executable not in self.allowed_commands:
            raise PermissionError(
                f"Command is not allowed: {executable}"
            )

        completed = subprocess.run(
            list(command),
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

        return {
            "command": list(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": (
                "passed"
                if completed.returncode == 0
                else "failed"
            ),
        }
