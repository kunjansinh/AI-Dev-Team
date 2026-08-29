from __future__ import annotations

from typing import Any

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.tools.llm.model_router import RoutedAgentClient


class BaseAgent:
    """Common foundation for every AI agent in the development team."""

    def __init__(
        self,
        name: str,
        role: str,
        state_manager: StateManager,
        task_manager: TaskManager,
        llm_client: RoutedAgentClient,
    ) -> None:
        self.name = name
        self.role = role
        self.state_manager = state_manager
        self.task_manager = task_manager
        self.llm_client = llm_client

        self._register_agent()

    def _register_agent(self) -> None:
        """Register the agent and mark it as available."""

        agents = self.state_manager.load_agents()

        agents[self.name] = {
            "name": self.name,
            "role": self.role,
            "status": "available",
        }

        self.state_manager.save_agents(agents)

    def _update_agent_status(self, status: str) -> None:
        """Update this agent's current status."""

        agents = self.state_manager.load_agents()

        if self.name not in agents:
            agents[self.name] = {
                "name": self.name,
                "role": self.role,
            }

        agents[self.name]["status"] = status

        self.state_manager.save_agents(agents)

    def _build_prompt(self, task: dict[str, Any]) -> str:
        """Build the prompt sent to the AI model."""

        previous_review = task.get(
            "review_feedback",
            "No previous Manager review feedback. This is the first attempt.",
        )

        return f"""
You are the {self.role} agent named {self.name}.

Your responsibilities:
{self.role}

Task:
ID: {task["id"]}
Title: {task["title"]}
Description: {task["description"]}
Priority: {task["priority"]}

Previous Manager Review:
{previous_review}

Your job is to work on the assigned task and provide a useful result.

If this is a rework iteration, you MUST address the concrete issues in the
previous Manager review. Do not simply repeat the previous implementation.
Only make changes that are relevant to the task and the review feedback.

Do not claim the task is complete unless you actually have evidence.
Explain important assumptions, limitations, and problems you encounter.
""".strip()

    def execute(self, task_id: str) -> dict[str, Any]:
        """Execute an assigned task using the configured AI model."""

        task = self.task_manager.get_task(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.task_manager.assign_task(task_id, self.name)
        self._update_agent_status("working")

        checkpoint = {
            "task_id": task_id,
            "agent": self.name,
            "status": "started",
            "iteration": task["iteration"],
        }

        self.state_manager.create_checkpoint(
            task_id,
            checkpoint,
        )

        try:
            prompt = self._build_prompt(task)
            result = self.llm_client.generate(prompt)

            updated_task = self.task_manager.record_result(
                task_id,
                result,
                progress=100,
            )

            updated_task = self.task_manager.update_status(
                task_id,
                "review",
            )

            final_checkpoint = {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "iteration": updated_task["iteration"],
                "result": result,
            }

            self.state_manager.create_checkpoint(
                task_id,
                final_checkpoint,
            )

            self._update_agent_status("available")

            return {
                "task_id": task_id,
                "agent": self.name,
                "status": "awaiting_review",
                "result": result,
            }

        except Exception as exc:
            self.task_manager.record_error(
                task_id,
                str(exc),
            )

            self._update_agent_status("error")

            error_checkpoint = {
                "task_id": task_id,
                "agent": self.name,
                "status": "error",
                "iteration": task["iteration"],
                "error": str(exc),
            }

            self.state_manager.create_checkpoint(
                task_id,
                error_checkpoint,
            )

            raise

    def report(self) -> dict[str, Any]:
        """Return the current agent status."""

        agents = self.state_manager.load_agents()

        return agents.get(
            self.name,
            {
                "name": self.name,
                "role": self.role,
                "status": "unknown",
            },
        )
