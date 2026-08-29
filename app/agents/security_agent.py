from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent


class SecurityAgent(BaseAgent):
    """Agent responsible for security analysis and risk identification."""

    task_type = "security"

    capabilities = {
        "security",
        "threat_modeling",
        "vulnerability_analysis",
    }

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
    ) -> None:
        super().__init__(
            name="security",
            role="Security Engineer",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

    def execute(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Perform a security review and return structured evidence."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(
            task_id,
            self.name,
        )

        self._update_agent_status("working")

        prompt = self._build_security_prompt(task)

        try:
            response = self.llm_client.generate(
                prompt,
                think=False,
            )

            security_review = self._parse_json_response(
                response
            )

            result = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": task["iteration"],
                "security_review": security_review,
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
                "security_review": {},
                "error": str(exc),
            }

    def _build_security_prompt(
        self,
        task: dict[str, Any],
    ) -> str:
        """Build a security-review prompt."""

        return f"""
You are the Security Engineer of a professional AI development team.

Task:
Title: {task["title"]}

Description:
{task["description"]}

Review the task for concrete security risks.

Consider:
- authentication and authorization
- input validation
- secrets and credentials
- sensitive data
- filesystem access
- command execution
- injection risks
- dependency risks
- error handling
- logging and information disclosure
- abuse cases

Do not invent vulnerabilities without a reasonable technical basis.

Return ONLY valid JSON:

{{
    "risk_level": "low or medium or high or critical",
    "findings": [
        {{
            "risk": "risk",
            "severity": "low or medium or high or critical",
            "reason": "technical reason",
            "mitigation": "recommended mitigation"
        }}
    ],
    "security_requirements": [
        "requirement"
    ],
    "recommendation": "security recommendation"
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
            "Security agent returned invalid JSON."
        )