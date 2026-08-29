from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent
from app.tools.testing import TestingTool


class QAAgent(BaseAgent):
    """Agent responsible for quality assurance and testing."""

    task_type = "qa"

    capabilities = {
        "quality_assurance",
        "testing",
        "validation",
    }

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
        workspace: str = "projects/demo_project",
        testing_tool: TestingTool | None = None,
    ) -> None:
        super().__init__(
            name="qa",
            role="Quality Assurance Engineer",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

        self.workspace = workspace
        self.testing_tool = (
            testing_tool
            or TestingTool()
        )

    def execute(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Run validation and produce QA evidence."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(
            task_id,
            self.name,
        )

        self._update_agent_status("working")

        try:
            validation = self.testing_tool.run_pytest(
                self.workspace
            )

            result = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": task["iteration"],
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
                "validation": {
                    "status": "error",
                    "error": str(exc),
                },
            }

    def build_test_plan(
        self,
        task: dict[str, Any],
    ) -> str:
        """Ask the QA model for a focused test plan."""

        prompt = f"""
You are the QA Engineer.

Task:
{task["title"]}

Description:
{task["description"]}

Create a concise test plan covering:
- happy paths
- invalid inputs
- edge cases
- regression risks
- security-sensitive cases where relevant

Return ONLY valid JSON:

{{
    "test_cases": [
        {{
            "name": "test name",
            "purpose": "what it verifies"
        }}
    ]
}}
""".strip()

        return self.llm_client.generate(
            prompt,
            think=False,
        )