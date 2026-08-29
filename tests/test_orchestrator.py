from pathlib import Path

import pytest

from app.core.orchestrator import Orchestrator
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class FakeAgent:
    """Fake specialist agent used for Orchestrator tests."""

    def __init__(
        self,
        name: str = "developer",
    ) -> None:
        self.name = name
        self.execute_count = 0

    def execute(self, task_id: str) -> dict:
        self.execute_count += 1

        return {
            "task_id": task_id,
            "agent": self.name,
            "status": "awaiting_review",
            "result": f"Attempt {self.execute_count}",
        }


class FakeManager:
    """Fake Manager that behaves like the real Manager contract."""

    def __init__(
        self,
        task_manager: TaskManager,
        decisions: list[str],
    ) -> None:
        self.task_manager = task_manager
        self.decisions = decisions
        self.review_count = 0

    def review_task(
        self,
        task_id: str,
        evidence: dict,
    ) -> dict:
        self.review_count += 1

        if self.decisions:
            decision = self.decisions.pop(0)
        else:
            decision = "BLOCK"

        if decision == "ACCEPT":
            self.task_manager.update_status(
                task_id,
                "done",
            )

        elif decision == "REWORK":
            self.task_manager.update_status(
                task_id,
                "rework",
            )

        elif decision == "BLOCK":
            self.task_manager.block_task(
                task_id,
                "Manager blocked the task.",
            )

        return {
            "decision": decision,
            "reason": f"Manager decision: {decision}",
            "evidence_received": evidence,
        }


@pytest.fixture
def orchestrator_components(
    tmp_path: Path,
):
    state_manager = StateManager(tmp_path / "state")
    task_manager = TaskManager(state_manager)

    manager = FakeManager(
        task_manager=task_manager,
        decisions=["ACCEPT"],
    )

    orchestrator = Orchestrator(
        state_manager=state_manager,
        task_manager=task_manager,
        manager_agent=manager,
        max_iterations=3,
    )

    agent = FakeAgent()

    orchestrator.register_agent(agent)

    return (
        state_manager,
        task_manager,
        manager,
        agent,
        orchestrator,
    )


def test_agent_can_be_registered(
    orchestrator_components,
) -> None:
    _, _, _, _, orchestrator = orchestrator_components

    assert "developer" in orchestrator.list_agents()


def test_unregistered_agent_is_rejected(
    orchestrator_components,
) -> None:
    _, _, _, _, orchestrator = orchestrator_components

    with pytest.raises(
        ValueError,
        match="Agent is not registered",
    ):
        orchestrator.get_agent("unknown")


def test_task_is_accepted_without_rework(
    orchestrator_components,
) -> None:
    (
        state_manager,
        task_manager,
        manager,
        agent,
        orchestrator,
    ) = orchestrator_components

    task = task_manager.create_task(
        title="Build feature",
        description="Implement the feature.",
    )

    result = orchestrator.run_task(
        task_id=task["id"],
        agent_name="developer",
    )

    updated_task = task_manager.get_task(task["id"])
    project_state = state_manager.load_project_state()

    assert result["status"] == "done"
    assert result["attempts"] == 1

    assert updated_task is not None
    assert updated_task["status"] == "done"

    assert agent.execute_count == 1
    assert manager.review_count == 1

    assert project_state["current_task"] is None
    assert project_state["status"] == "idle"


def test_rework_causes_another_iteration(
    orchestrator_components,
) -> None:
    (
        _,
        task_manager,
        manager,
        agent,
        orchestrator,
    ) = orchestrator_components

    manager.decisions = [
        "REWORK",
        "ACCEPT",
    ]

    task = task_manager.create_task(
        title="Build feature",
        description="Implement the feature.",
    )

    result = orchestrator.run_task(
        task_id=task["id"],
        agent_name="developer",
    )

    updated_task = task_manager.get_task(task["id"])

    assert result["status"] == "done"
    assert result["attempts"] == 2

    assert updated_task is not None
    assert updated_task["status"] == "done"
    assert updated_task["iteration"] == 1

    assert agent.execute_count == 2
    assert manager.review_count == 2


def test_block_decision_stops_execution(
    orchestrator_components,
) -> None:
    (
        _,
        task_manager,
        manager,
        agent,
        orchestrator,
    ) = orchestrator_components

    manager.decisions = ["BLOCK"]

    task = task_manager.create_task(
        title="Deploy application",
        description="Deploy to production.",
    )

    result = orchestrator.run_task(
        task_id=task["id"],
        agent_name="developer",
    )

    updated_task = task_manager.get_task(task["id"])

    assert result["status"] == "blocked"

    assert updated_task is not None
    assert updated_task["status"] == "blocked"

    assert agent.execute_count == 1
    assert manager.review_count == 1


def test_max_iterations_block_task(
    tmp_path: Path,
) -> None:
    state_manager = StateManager(tmp_path / "state")
    task_manager = TaskManager(state_manager)

    manager = FakeManager(
        task_manager=task_manager,
        decisions=[
            "REWORK",
            "REWORK",
            "REWORK",
        ],
    )

    orchestrator = Orchestrator(
        state_manager=state_manager,
        task_manager=task_manager,
        manager_agent=manager,
        max_iterations=3,
    )

    agent = FakeAgent()

    orchestrator.register_agent(agent)

    task = task_manager.create_task(
        title="Impossible task",
        description="Always returns a failing result.",
    )

    result = orchestrator.run_task(
        task_id=task["id"],
        agent_name="developer",
    )

    updated_task = task_manager.get_task(task["id"])

    assert result["status"] == "blocked"
    assert result["attempts"] == 3

    assert updated_task is not None
    assert updated_task["status"] == "blocked"
    assert updated_task["iteration"] == 2

    assert agent.execute_count == 3
    assert manager.review_count == 3