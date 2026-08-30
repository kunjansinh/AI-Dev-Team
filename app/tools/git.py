from __future__ import annotations

import subprocess
from pathlib import Path


class GitTool:
    """Read-only Git inspection for an agent workspace."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def _run(self, *args: str) -> dict:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        return {
            "command": ["git", *args],
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": "passed" if completed.returncode == 0 else "failed",
        }

    def status(self) -> dict:
        return self._run("status", "--short", "--branch")

    def diff(self) -> dict:
        return self._run("diff", "--")
