from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class TestingTool:
    """Run pytest safely inside a project workspace."""

    def run_pytest(
        self,
        workspace: str | Path,
    ) -> dict[str, Any]:
        """
        Run pytest using the current Python interpreter.

        The tool never raises merely because tests fail.
        Test failure is returned as structured evidence so the
        Manager can decide whether the task needs rework.
        """

        workspace_path = Path(workspace).resolve()

        if not workspace_path.exists():
            return {
                "status": "error",
                "exit_code": None,
                "tests_collected": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "command": [],
                "output": "",
                "error": f"Workspace does not exist: {workspace_path}",
            }

        command = [
            sys.executable,
            "-m",
            "pytest",
            str(workspace_path),
            "-v",
            "--tb=short",
        ]

        try:
            completed = subprocess.run(
                command,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

        except subprocess.TimeoutExpired as exc:
            output = "\n".join(
                part
                for part in [
                    exc.stdout or "",
                    exc.stderr or "",
                ]
                if part
            )

            return {
                "status": "timeout",
                "exit_code": None,
                "tests_collected": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
                "command": command,
                "output": output,
                "error": "pytest timed out after 120 seconds.",
            }

        output = "\n".join(
            part
            for part in [
                completed.stdout,
                completed.stderr,
            ]
            if part
        )

        collected = self._extract_number(
            r"collected\s+(\d+)\s+items?",
            output,
        )

        passed = self._extract_number(
            r"(\d+)\s+passed",
            output,
        )

        failed = self._extract_number(
            r"(\d+)\s+failed",
            output,
        )

        skipped = self._extract_number(
            r"(\d+)\s+skipped",
            output,
        )

        # pytest exit code 5 means no tests were collected.
        if completed.returncode == 5 or collected == 0:
            status = "no_tests"
        elif completed.returncode == 0 and failed == 0:
            status = "passed"
        else:
            status = "failed"

        return {
            "status": status,
            "exit_code": completed.returncode,
            "tests_collected": collected,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_skipped": skipped,
            "command": command,
            "output": output,
            "error": None,
        }

    @staticmethod
    def _extract_number(
        pattern: str,
        text: str,
    ) -> int:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            return 0

        return int(match.group(1))