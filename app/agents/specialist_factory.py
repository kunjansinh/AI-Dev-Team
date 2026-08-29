from __future__ import annotations

from typing import Any

from app.agents.architect_agent import ArchitectAgent
from app.agents.qa_agent import QAAgent
from app.agents.researcher_agent import ResearcherAgent
from app.agents.security_agent import SecurityAgent
from app.tools.llm.model_router import ModelRouter


class RoutedAgentClient:
    """Adapter that routes an agent request through ModelRouter."""

    def __init__(
        self,
        router: ModelRouter,
        task_type: str,
    ) -> None:
        self.router = router
        self.task_type = task_type

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Generate using the model selected for this task type."""

        return self.router.generate(
            prompt=prompt,
            task_type=self.task_type,
            think=think,
        )


def create_specialist_agents(
    state_manager: Any,
    task_manager: Any,
    router: ModelRouter | None = None,
) -> dict[str, Any]:
    """
    Create the complete specialist team.

    Each specialist declares:
    - task_type: used for model routing
    - capabilities: used for capability-based delegation
    """

    model_router = router or ModelRouter()

    return {
        "architect": ArchitectAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                model_router,
                ArchitectAgent.task_type,
            ),
        ),
        "researcher": ResearcherAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                model_router,
                ResearcherAgent.task_type,
            ),
        ),
        "qa": QAAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                model_router,
                QAAgent.task_type,
            ),
        ),
        "security": SecurityAgent(
            state_manager=state_manager,
            task_manager=task_manager,
            llm_client=RoutedAgentClient(
                model_router,
                SecurityAgent.task_type,
            ),
        ),
    }