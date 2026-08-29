from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    """Agent responsible for system architecture and technical design."""

    task_type = "architecture"

    capabilities = {
        "architecture",
        "system_design",
        "technology_selection",
    }

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
    ) -> None:
        super().__init__(
            name="architect",
            role="Software Architect",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

    def execute(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Produce an architecture decision and technical evidence."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(
            task_id,
            self.name,
        )

        self._update_agent_status("working")

        prompt = self._build_architecture_prompt(task)

        try:
            response = self.llm_client.generate(
                prompt,
                think=False,
            )

            architecture = self._parse_json_response(
                response
            )

            result = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": task["iteration"],
                "architecture": architecture,
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
                "architecture": {},
                "error": str(exc),
            }

    def _build_architecture_prompt(
        self,
        task: dict[str, Any],
    ) -> str:
        """Build an architecture-specific prompt."""

        return f"""
You are the Software Architect of a professional AI development team.

Task:
Title: {task["title"]}

Description:
{task["description"]}

Produce a practical architecture for this task.

Consider:
- system components
- responsibilities
- interfaces
- data flow
- dependencies
- technology choices
- scalability
- security
- testing strategy
- important trade-offs
- assumptions and risks

Do not invent requirements that are not justified by the task.

Return ONLY valid JSON:

{{
    "summary": "architecture summary",
    "components": [
        {{
            "name": "component name",
            "responsibility": "responsibility"
        }}
    ],
    "interfaces": [
        "interface or boundary"
    ],
    "data_flow": [
        "step 1"
    ],
    "technology_choices": [
        {{
            "technology": "technology",
            "reason": "reason"
        }}
    ],
    "risks": [
        "risk"
    ],
    "trade_offs": [
        "trade-off"
    ],
    "testing_strategy": [
        "test strategy"
    ]
}}
""".strip()

    @staticmethod
    def _parse_json_response(
        response: str,
    ) -> dict[str, Any]:
        """Extract a JSON object from the model response."""

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

            if isinstance(data, dict):
                return data

        raise ValueError(
            "Architect returned invalid JSON."
        )