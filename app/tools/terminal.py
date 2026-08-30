from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


class TerminalTool:
    """Run approved commands inside a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        command: Sequence[str],
        timeout: int = 120,
    ) -> dict:
        if not command:
            raise ValueError("Command cannot be empty.")

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
            "status": "passed" if completed.returncode == 0 else "failed",
        }
