from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent


class ManagerAgent(BaseAgent):
    """Technical leader responsible for planning, delegation, and review."""

    MANAGER_RULES = """
You are the Manager and technical leader of an AI software development team.

You are NOT a yes-man.

Your responsibilities:
- Understand the user's objective.
- Challenge weak or unnecessary ideas.
- Identify assumptions, risks, and trade-offs.
- Recommend better alternatives when appropriate.
- Break approved objectives into practical tasks.
- Delegate work to specialist agents.
- Review evidence from agents.
- Reject incomplete or poor work.
- Request rework when necessary.
- Block tasks when they cannot safely continue.
- Never claim something is complete without evidence.

Decision authority:
- The human is the final authority.
- You provide honest technical leadership.
- You may strongly disagree with the human.
- You must explain disagreements using technical reasoning.

Quality rules:
- No evidence = not complete.
- Distinguish between impossible, possible but impractical, and recommended.
- Do not invent test results, files, implementation details, or approvals.
- Consider the actual hardware, project constraints, and available resources.

Review discipline:
- Judge the implementation against the TASK's explicit requirements first.
- Passing validation and tests are strong evidence when they directly exercise
  the requested behavior.
- ACCEPT when the explicit requirements are satisfied and the evidence supports
  that conclusion.
- REWORK only when there is a concrete unmet requirement, failed validation,
  unsafe behavior, contradictory evidence, or important missing evidence.
- Do not invent additional requirements that the user did not request.
- Do not request rework merely because the code could be made more elegant,
  more defensive, more feature-rich, or more comprehensive.
- Optional hardening and future improvements belong in recommendations, not in a
  REWORK decision unless they are required for correctness or safety.
- If tests pass but a required behavior is not actually covered, identify the
  specific missing evidence instead of making a vague quality complaint.
- BLOCK only when the task cannot safely or meaningfully continue and explain why.
- For REWORK, every missing_evidence item must be concrete and testable.
""".strip()

    VALID_REVIEW_DECISIONS = {
        "ACCEPT",
        "REWORK",
        "BLOCK",
    }

    MAX_JSON_RETRIES = 1

    def __init__(
        self,
        state_manager,
        task_manager,
        llm_client,
    ) -> None:
        super().__init__(
            name="manager",
            role="Technical Manager",
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=llm_client,
        )

    def build_manager_prompt(
        self,
        instruction: str,
    ) -> str:
        """Build the Manager's system-level instruction."""

        return f"""
{self.MANAGER_RULES}

Current user instruction:
{instruction}

Provide a concise, technically justified response.
""".strip()

    def classify_task(
        self,
        instruction: str,
    ) -> dict[str, Any]:
        """Classify a user request into a specialist capability."""

        prompt = self.build_manager_prompt(
            f"""
Analyze this software-development request:

{instruction}

Return ONLY valid JSON:

{{
    "task_title": "short task title",
    "description": "clear implementation description",
    "capability": "coding" or "architecture" or "research" or "testing" or "security",
    "priority": "low" or "medium" or "high"
}}

Choose the single capability that best matches the main work.
Do not choose multiple capabilities.
"""
        )

        return self._generate_json_with_retry(prompt)

    def evaluate_proposal(
        self,
        proposal: str,
    ) -> dict[str, Any]:
        """Critically evaluate a proposal using the local model."""

        prompt = self.build_manager_prompt(
            f"""
Critically evaluate this proposal:

{proposal}

Return JSON only using this structure:

{{
    "decision": "APPROVE" or "REJECT" or "APPROVE_WITH_CHANGES",
    "reason": "technical reasoning",
    "risks": ["risk 1", "risk 2"],
    "alternatives": ["alternative 1"],
    "recommended_action": "what should happen next"
}}
"""
        )

        return self._generate_json_with_retry(prompt)

    def create_task_from_instruction(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """Create a task under the Manager's authority."""

        return self.task_manager.create_task(
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
        )

    def review_task(
        self,
        task_id: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Review task evidence and decide whether to accept the work."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        evidence_text = json.dumps(
            evidence,
            indent=2,
        )

        prompt = self.build_manager_prompt(
            f"""
Review this task against its explicit requirements.

TASK:
{json.dumps(task, indent=2)}

EVIDENCE:
{evidence_text}

Review procedure:
1. Identify the explicit requirements in TASK.description.
2. Check whether the evidence demonstrates each requirement.
3. Treat successful automated validation as strong evidence when it directly
   covers the requested behavior.
4. ACCEPT if the requirements are satisfied and there is no concrete correctness
   or safety problem.
5. REWORK only for a concrete unmet requirement, failed validation, unsafe
   behavior, contradictory evidence, or important missing evidence.
6. Do NOT reject working code merely because additional edge cases, hardening,
   refactoring, standards, or tests could be added beyond the explicit task.
7. BLOCK only when the task cannot safely continue.

For REWORK, state exactly what must change and how it can be verified.
For ACCEPT, state what evidence proves the task is complete.

Return JSON only using this structure:

{{
    "decision": "ACCEPT" or "REWORK" or "BLOCK",
    "reason": "technical reasoning tied to the explicit requirements",
    "missing_evidence": ["specific item, only when needed"],
    "next_action": "what should happen next"
}}
"""
        )

        decision = self._generate_json_with_retry(prompt)

        self._apply_review_decision(
            task_id,
            decision,
        )

        return decision

    def _generate_json_with_retry(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """Generate JSON from the model, retrying once if necessary."""

        last_error: ValueError | None = None
        current_prompt = prompt

        for attempt in range(self.MAX_JSON_RETRIES + 1):
            result = self.llm_client.generate(
                current_prompt,
                think=False,
            )

            try:
                return self._parse_json_result(result)

            except ValueError as exc:
                last_error = exc

                if attempt >= self.MAX_JSON_RETRIES:
                    break

                current_prompt = f"""
Your previous response was not valid JSON.

Return ONLY a valid JSON object.
Do not use markdown fences.
Do not add explanations before or after the JSON.

Original request:
{prompt}

Previous response:
{result}

Correct the response and return only valid JSON.
""".strip()

        raise ValueError(
            "Manager model failed to return valid JSON "
            f"after {self.MAX_JSON_RETRIES + 1} attempts."
        ) from last_error

    def _apply_review_decision(
        self,
        task_id: str,
        decision: dict[str, Any],
    ) -> None:
        """Apply the Manager's review decision to task state."""

        action = str(
            decision.get("decision", "")
        ).upper()

        if action not in self.VALID_REVIEW_DECISIONS:
            raise ValueError(
                f"Invalid Manager decision: {action}. "
                f"Expected one of "
                f"{sorted(self.VALID_REVIEW_DECISIONS)}."
            )

        if action == "ACCEPT":
            self.task_manager.update_status(
                task_id,
                "done",
            )

        elif action == "REWORK":
            self.task_manager.update_status(
                task_id,
                "rework",
            )

        elif action == "BLOCK":
            reason = decision.get(
                "reason",
                "Manager blocked the task.",
            )

            self.task_manager.block_task(
                task_id,
                str(reason),
            )

    @staticmethod
    def _parse_json_result(
        result: str,
    ) -> dict[str, Any]:
        """Parse a model response containing a JSON object."""

        cleaned = result.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Manager model returned invalid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Manager model response must be a JSON object."
            )

        return parsed
