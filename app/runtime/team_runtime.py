from __future__ import annotations

from typing import Any

from app.agents.developer_agent import DeveloperAgent
from app.agents.manager_agent import ManagerAgent
from app.agents.specialist_factory import RoutedAgentClient, create_specialist_agents
from app.core.agent_manager import AgentManager
from app.core.orchestrator import Orchestrator
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.tools.llm.model_router import ModelRouter
from app.tools.testing import TestingTool


class TeamRuntime:
    """Compose the AI development team around the existing core services.

    The runtime owns dependency wiring. Agents receive routed LLM clients,
    while the Orchestrator remains responsible for deterministic execution,
    review, rework, and blocking decisions.
    """

    def __init__(
        self,
        state_manager: StateManager,
        task_manager: TaskManager,
        router: ModelRouter | None = None,
        developer_workspace: str = "projects/demo_project",
        max_iterations: int = 3,
    ) -> None:
        self.state_manager = state_manager
        self.task_manager = task_manager
        self.router = router or ModelRouter()
        self.agent_manager = AgentManager()

        self.manager = ManagerAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                self.router,
                "management",
            ),
        )

        self.developer = DeveloperAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                self.router,
                "coding",
            ),
            workspace=developer_workspace,
            testing_tool=TestingTool(),
        )

        self.specialists = create_specialist_agents(
            state_manager=state_manager,
            task_manager=task_manager,
            router=self.router,
        )

        self._register_agents()

        self.orchestrator = Orchestrator(
            state_manager=state_manager,
            task_manager=task_manager,
            manager_agent=self.manager,
            max_iterations=max_iterations,
        )

        for agent_name in self.agent_manager.list_agents():
            self.orchestrator.register_agent(
                self.agent_manager.get_agent(agent_name)
            )

    def _register_agents(self) -> None:
        """Register all executable agents with their capabilities."""

        self.agent_manager.register_agent(
            self.developer,
            ["coding", "implementation"],
        )

        for name, agent in self.specialists.items():
            self.agent_manager.register_agent(
                agent,
                sorted(agent.capabilities),
            )

    def run(self, instruction: str) -> dict[str, Any]:
        """Let the Manager classify and execute one user instruction."""

        cleaned = instruction.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be empty.")

        classification = self.manager.classify_task(cleaned)

        required = {
            "task_title",
            "description",
            "capability",
            "priority",
        }
        missing = required - classification.keys()
        if missing:
            raise ValueError(
                "Manager classification is missing fields: "
                + ", ".join(sorted(missing))
            )

        capability = str(classification["capability"]).strip().lower()

        task = self.manager.create_task_from_instruction(
            title=str(classification["task_title"]),
            description=str(classification["description"]),
            priority=str(classification["priority"]),
        )

        result = self.orchestrator.run_task_by_capability(
            task_id=task["id"],
            capability=capability,
            agent_manager=self.agent_manager,
        )

        return {
            "instruction": cleaned,
            "classification": classification,
            "task": self.task_manager.get_task(task["id"]),
            "result": result,
        }

    def describe_team(self) -> dict[str, list[str]]:
        """Return the runtime's capability map."""
        return self.agent_manager.describe_team()
