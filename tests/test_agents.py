from pathlib import Path
from typing import Any

import pytest

from app.agents.base_agent import BaseAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class FakeLLMClient:
    """Fake model used for tests so we do not call Ollama."""

    def __init__(self, response: str = "Task completed successfully.") -> None:
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


@pytest.fixture
def test_components(
    tmp_path: Path,
) -> tuple[StateManager, TaskManager, FakeLLMClient]:
    state_manager = StateManager(tmp_path / "state")
    task_manager = TaskManager(state_manager)
    llm_client = FakeLLMClient()

    return state_manager, task_manager, llm_client


def test_agent_registers_itself(
    test_components: tuple[StateManager, TaskManager, FakeLLMClient],
) -> None:
    state_manager, task_manager, llm_client = test_components

    agent = BaseAgent(
        name="developer",
        role="Software Developer",
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm_client,
    )

    agents = state_manager.load_agents()

    assert "developer" in agents
    assert agents["developer"]["role"] == "Software Developer"
    assert agents["developer"]["status"] == "available"


def test_agent_executes_task_and_sends_it_to_review(
    test_components: tuple[StateManager, TaskManager, FakeLLMClient],
) -> None:
    state_manager, task_manager, llm_client = test_components

    agent = BaseAgent(
        name="developer",
        role="Software Developer",
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm_client,
    )

    task = task_manager.create_task(
        title="Build login API",
        description="Implement a login endpoint.",
    )

    result = agent.execute(task["id"])

    updated_task = task_manager.get_task(task["id"])

    assert updated_task is not None
    assert updated_task["assigned_to"] == "developer"
    assert updated_task["status"] == "review"
    assert updated_task["progress"] == 100
    assert updated_task["result"] == "Task completed successfully."

    assert result["task_id"] == task["id"]
    assert result["status"] == "awaiting_review"


def test_agent_creates_checkpoint(
    test_components: tuple[StateManager, TaskManager, FakeLLMClient],
) -> None:
    state_manager, task_manager, llm_client = test_components

    agent = BaseAgent(
        name="architect",
        role="Software Architect",
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm_client,
    )

    task = task_manager.create_task(
        title="Design architecture",
        description="Create the initial architecture.",
    )

    agent.execute(task["id"])

    checkpoint = state_manager.load_checkpoint(task["id"])

    assert checkpoint is not None
    assert checkpoint["task_id"] == task["id"]
    assert checkpoint["agent"] == "architect"
    assert checkpoint["status"] == "awaiting_review"


def test_agent_reports_current_status(
    test_components: tuple[StateManager, TaskManager, FakeLLMClient],
) -> None:
    state_manager, task_manager, llm_client = test_components

    agent = BaseAgent(
        name="qa",
        role="Quality Assurance Engineer",
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm_client,
    )

    report = agent.report()

    assert report["name"] == "qa"
    assert report["role"] == "Quality Assurance Engineer"
    assert report["status"] == "available"