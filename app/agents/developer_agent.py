from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.tool_manager import ToolManager
from app.tools.testing import TestingTool


class DeveloperAgent(BaseAgent):
    """Agent responsible for implementation and validation."""

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
        workspace: str = "projects/demo_project",
        testing_tool: TestingTool | None = None,
        tool_manager: ToolManager | None = None,
    ) -> None:
        super().__init__(
            name="developer",
            role="Software Developer",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.testing_tool = testing_tool or TestingTool()
        self.tool_manager = tool_manager

    def execute(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Implement a task, validate it, and return evidence."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(
            task_id,
            self.name,
        )

        self._update_agent_status("working")

        prompt = self._build_developer_prompt(task)

        try:
            raw_result = self.llm_client.generate(
                prompt,
                think=False,
            )

            generated_files = self._parse_generated_files(
                raw_result
            )

            written_files: list[str] = []

            for relative_path, content in generated_files.items():
                written_files.append(
                    self._write_generated_file(
                        relative_path,
                        content,
                    )
                )

            has_tests = self._contains_test_file(
                written_files
            )

            if not has_tests:
                validation = {
                    "status": "no_tests",
                    "exit_code": 5,
                    "tests_collected": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "tests_skipped": 0,
                    "output": "",
                    "error": (
                        "Developer did not generate "
                        "a pytest test file."
                    ),
                }
            else:
                validation = self._run_validation()

            result = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": task["iteration"],
                "written_files": written_files,
                "validation": validation,
            }

            self.task_manager.record_result(
                task_id,
                json.dumps(
                    result,
                    indent=2,
                ),
                progress=100,
            )

            self.task_manager.update_status(
                task_id,
                "review",
            )

            self._update_agent_status("available")

            return result

        except Exception as exc:
            self.task_manager.record_error(
                task_id,
                str(exc),
            )

            self._update_agent_status("error")

            return {
                "task_id": task_id,
                "agent": self.name,
                "status": "error",
                "iteration": task["iteration"],
                "written_files": [],
                "validation": {
                    "status": "error",
                    "tests_collected": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "tests_skipped": 0,
                    "error": str(exc),
                },
            }

    def _write_generated_file(
        self,
        relative_path: str,
        content: str,
    ) -> str:
        """Write through the controlled tool gateway when configured."""

        path = self._safe_workspace_path(relative_path)

        if self.tool_manager is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return str(path.relative_to(self.workspace)).replace("\\", "/")

        tool_name = "modify_file" if path.exists() else "create_file"
        result = self.tool_manager.execute(
            self.name,
            tool_name,
            relative_path=relative_path,
            content=content,
        )

        if result["status"] != "success":
            raise PermissionError(
                result.get("error", "Tool execution failed.")
            )

        return str(result["result"])

    def _run_validation(self) -> dict[str, Any]:
        """Run pytest through the controlled tool gateway when configured."""

        if self.tool_manager is None:
            return self.testing_tool.run_pytest(self.workspace)

        result = self.tool_manager.execute(
            self.name,
            "run_tests",
        )

        if result["status"] != "success":
            raise RuntimeError(
                result.get("error", "Test tool failed.")
            )

        return result["result"]

    def _build_developer_prompt(
        self,
        task: dict[str, Any],
    ) -> str:
        """Build an implementation prompt with rework context."""

        previous_feedback = task.get(
            "review_feedback"
        )

        feedback_section = (
            "No previous attempt. "
            "This is the first implementation."
        )

        if previous_feedback:
            feedback_section = f"""
This is a REWORK iteration.

The previous attempt was rejected by the Manager.

Previous Manager feedback:
{json.dumps(previous_feedback, indent=2)}

You MUST address every issue in that feedback.
Do not repeat the same mistake.
"""

        return f"""
You are the Developer Agent in a professional software
development team.

Task:
Title: {task["title"]}

Description:
{task["description"]}

Current iteration:
{task["iteration"]}

{feedback_section}

Your job is to produce a working implementation.

For a coding task you MUST create:
1. Implementation file(s).
2. At least one pytest test file.

Return one JSON object with this exact structure:

{{
    "files": {{
        "relative/path.py": "complete file contents"
    }}
}}

IMPORTANT OUTPUT RULES:
- Your final response must contain the JSON object.
- Do not use markdown code fences.
- Do not add commentary before or after the JSON.
- Do not include a "```json" wrapper.
- Use valid JSON string escaping.
- Newlines inside file contents must be escaped correctly as JSON.
- Use relative paths only.
- Never use '..' in paths.
- Never use absolute paths.
- Test filenames must begin with "test_" or end with "_test.py".
- Tests must directly verify the requested behaviour.
- Keep the implementation simple and correct.
- Do not invent unnecessary dependencies.
- On rework, explicitly correct the previous failure.
""".strip()

    @staticmethod
    def _contains_test_file(
        files: list[str],
    ) -> bool:
        """Check whether generated files include a pytest test."""

        for file_name in files:
            name = Path(
                file_name.replace("\\", "/")
            ).name

            if name.startswith("test_") and name.endswith(".py"):
                return True

            if name.endswith("_test.py"):
                return True

        return False

    @staticmethod
    def _parse_generated_files(
        response: str,
    ) -> dict[str, str]:
        """
        Extract and validate the generated-file JSON.

        The local model may return surrounding text,
        markdown fences, or reasoning despite being instructed
        to return JSON only.
        """

        if not isinstance(response, str):
            raise ValueError(
                "Developer response must be a string."
            )

        cleaned = response.strip()

        if not cleaned:
            raise ValueError(
                "Developer returned an empty response."
            )

        data = DeveloperAgent._extract_json_object(
            cleaned
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Developer response must contain a JSON object."
            )

        files = data.get("files")

        if not isinstance(files, dict) or not files:
            raise ValueError(
                "Developer response must contain "
                "a non-empty 'files' object."
            )

        validated_files: dict[str, str] = {}

        for path, content in files.items():
            if not isinstance(path, str):
                raise ValueError(
                    "Generated file path must be a string."
                )

            if not path.strip():
                raise ValueError(
                    "Generated file path cannot be empty."
                )

            if not isinstance(content, str):
                raise ValueError(
                    "Generated file content must be a string: "
                    f"{path}"
                )

            validated_files[path] = content

        return validated_files

    @staticmethod
    def _extract_json_object(
        response: str,
    ) -> dict[str, Any]:
        """
        Extract the first valid JSON object containing 'files'.

        Handles plain JSON, fenced JSON, surrounding explanations,
        reasoning before JSON, and trailing text.
        """

        decoder = json.JSONDecoder()

        for index, character in enumerate(response):
            if character != "{":
                continue

            try:
                data, _ = decoder.raw_decode(
                    response[index:]
                )
            except json.JSONDecodeError:
                continue

            if (
                isinstance(data, dict)
                and "files" in data
            ):
                return data

        raise ValueError(
            "Developer returned invalid JSON or "
            "JSON did not contain a 'files' object."
        )

    def _safe_workspace_path(
        self,
        relative_path: str,
    ) -> Path:
        """Prevent generated files from escaping the workspace."""

        normalized_path = relative_path.replace(
            "\\",
            "/",
        )

        if Path(normalized_path).is_absolute():
            raise PermissionError(
                f"Unsafe workspace path: {relative_path}"
            )

        if any(
            part == ".."
            for part in Path(normalized_path).parts
        ):
            raise PermissionError(
                f"Unsafe workspace path: {relative_path}"
            )

        candidate = (
            self.workspace / normalized_path
        ).resolve()

        try:
            candidate.relative_to(
                self.workspace
            )
        except ValueError as exc:
            raise PermissionError(
                f"Unsafe workspace path: {relative_path}"
            ) from exc

        return candidate