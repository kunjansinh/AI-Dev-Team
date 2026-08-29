from __future__ import annotations

import json
from typing import Any

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class Orchestrator:
    """
    Coordinates agents, task execution, Manager review,
    rework loops, and task recovery.
    """

    def __init__(
        self,
        state_manager: StateManager,
        task_manager: TaskManager,
        manager_agent: Any,
        max_iterations: int = 3,
    ) -> None:
        if max_iterations < 1:
            raise ValueError(
                "max_iterations must be at least 1."
            )

        self.state_manager = state_manager
        self.task_manager = task_manager
        self.manager_agent = manager_agent
        self.max_iterations = max_iterations

        self.agents: dict[str, Any] = {}

    def register_agent(self, agent: Any) -> None:
        """Register an executable agent."""

        if not getattr(agent, "name", None):
            raise ValueError(
                "Agent must have a name."
            )

        self.agents[agent.name] = agent

    def get_agent(self, agent_name: str) -> Any:
        """Return a registered agent."""

        agent = self.agents.get(agent_name)

        if agent is None:
            raise ValueError(
                f"Agent is not registered: {agent_name}"
            )

        return agent

    def list_agents(self) -> list[str]:
        """Return all registered agent names."""

        return list(self.agents.keys())

    def run_task_by_capability(
        self,
        task_id: str,
        capability: str,
        agent_manager: Any,
    ) -> dict[str, Any]:
        """Find an agent by capability and execute the task."""

        agent = agent_manager.find_agent_by_capability(
            capability
        )

        return self.run_task(
            task_id=task_id,
            agent_name=agent.name,
        )

    def run_task(
        self,
        task_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        """
        Execute a task and run the Manager-controlled
        accept/rework/block loop.
        """

        task = self.task_manager.get_task(
            task_id
        )

        if task is None:
            raise ValueError(
                f"Task not found: {task_id}"
            )

        agent = self.get_agent(
            agent_name
        )

        self.state_manager.update_project_state(
            current_task=task_id,
            status="running",
        )

        for attempt in range(
            self.max_iterations
        ):
            current_task = self.task_manager.get_task(
                task_id
            )

            if current_task is None:
                raise ValueError(
                    f"Task disappeared: {task_id}"
                )

            result = agent.execute(
                task_id
            )

            evidence = {
                "attempt": attempt + 1,
                "agent": agent_name,
                "task_result": result,
            }

            decision = self.manager_agent.review_task(
                task_id,
                evidence,
            )

            decision_name = str(
                decision.get(
                    "decision",
                    "",
                )
            ).upper()

            # -------------------------------------------------
            # ACCEPT
            # -------------------------------------------------
            if decision_name == "ACCEPT":
                self.state_manager.update_project_state(
                    current_task=None,
                    status="idle",
                )

                return {
                    "task_id": task_id,
                    "status": "done",
                    "attempts": attempt + 1,
                    "decision": decision,
                }

            # -------------------------------------------------
            # BLOCK
            # -------------------------------------------------
            if decision_name == "BLOCK":
                self.state_manager.update_project_state(
                    current_task=None,
                    status="blocked",
                )

                return {
                    "task_id": task_id,
                    "status": "blocked",
                    "attempts": attempt + 1,
                    "decision": decision,
                }

            # -------------------------------------------------
            # INVALID DECISION
            # -------------------------------------------------
            if decision_name != "REWORK":
                raise ValueError(
                    "Manager returned an unsupported "
                    f"decision: {decision_name}"
                )

            # -------------------------------------------------
            # BUILD REWORK FEEDBACK
            # -------------------------------------------------
            review_feedback = {
                "decision": decision_name,
                "reason": decision.get(
                    "reason"
                ),
                "missing_evidence": decision.get(
                    "missing_evidence",
                    [],
                ),
                "next_action": decision.get(
                    "next_action"
                ),
                "previous_validation": result.get(
                    "validation",
                    {},
                ),
            }

            # -------------------------------------------------
            # SAVE FEEDBACK INTO TASK STATE
            #
            # record_result() persists the whole task,
            # including review_feedback.
            # -------------------------------------------------
            current_task["review_feedback"] = (
                review_feedback
            )

            self.task_manager.record_result(
                task_id,
                json.dumps(
                    {
                        "previous_attempt": result,
                        "manager_feedback": review_feedback,
                    },
                    indent=2,
                ),
                progress=current_task.get(
                    "progress",
                    0,
                ),
            )

            # -------------------------------------------------
            # MAX ITERATIONS
            # -------------------------------------------------
            if attempt == self.max_iterations - 1:
                reason = (
                    "Maximum task iterations reached. "
                    "Human review is required."
                )

                self.task_manager.block_task(
                    task_id,
                    reason,
                )

                self.state_manager.update_project_state(
                    current_task=None,
                    status="blocked",
                )

                return {
                    "task_id": task_id,
                    "status": "blocked",
                    "attempts": attempt + 1,
                    "decision": {
                        "decision": "BLOCK",
                        "reason": reason,
                    },
                }

            # -------------------------------------------------
            # START NEXT ITERATION
            #
            # TaskManager preserves review_feedback because
            # it loads and saves the complete task object.
            # -------------------------------------------------
            self.task_manager.start_new_iteration(
                task_id
            )

        raise RuntimeError(
            "Orchestrator exited without a final decision."
        )

    def resume_task(
        self,
        task_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        """Resume an existing unfinished task."""

        task = self.task_manager.get_task(
            task_id
        )

        if task is None:
            raise ValueError(
                f"Task not found: {task_id}"
            )

        if task["status"] == "done":
            return {
                "task_id": task_id,
                "status": "done",
                "attempts": task["iteration"] + 1,
                "decision": {
                    "decision": "ALREADY_COMPLETE"
                },
            }

        if task["status"] == "blocked":
            return {
                "task_id": task_id,
                "status": "blocked",
                "attempts": task["iteration"] + 1,
                "decision": {
                    "decision": "ALREADY_BLOCKED"
                },
            }

        return self.run_task(
            task_id=task_id,
            agent_name=agent_name,
        )