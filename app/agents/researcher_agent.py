from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    """Agent responsible for technical research and requirements analysis."""

    task_type = "research"

    capabilities = {
        "requirements_analysis",
        "research",
        "technology_research",
    }

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
    ) -> None:
        super().__init__(
            name="researcher",
            role="Technical Researcher",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

    def execute(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Research a task and return structured findings."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(
            task_id,
            self.name,
        )

        self._update_agent_status("working")

        prompt = self._build_research_prompt(task)

        try:
            response = self.llm_client.generate(
                prompt,
                think=False,
            )

            research = self._parse_json_response(
                response
            )

            result = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": task["iteration"],
                "research": research,
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
                "research": {},
                "error": str(exc),
            }

    def _build_research_prompt(
        self,
        task: dict[str, Any],
    ) -> str:
        """Build a research-specific prompt."""

        return f"""
You are the Technical Researcher of a professional AI development team.

Task:
Title: {task["title"]}

Description:
{task["description"]}

Research the technical problem and provide useful evidence for
the Manager and other specialists.

You must:
- identify relevant technical facts
- compare practical alternatives
- identify constraints
- identify risks
- distinguish facts from assumptions
- avoid inventing sources or evidence

If external research is unavailable, explicitly state that limitation.

Return ONLY valid JSON:

{{
    "summary": "research summary",
    "findings": [
        {{
            "finding": "finding",
            "confidence": "high or medium or low",
            "basis": "basis or reasoning"
        }}
    ],
    "alternatives": [
        {{
            "option": "option",
            "advantages": ["advantage"],
            "disadvantages": ["disadvantage"]
        }}
    ],
    "constraints": [
        "constraint"
    ],
    "risks": [
        "risk"
    ],
    "recommendation": "recommended direction",
    "limitations": [
        "research limitation"
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
            "Researcher returned invalid JSON."
        )