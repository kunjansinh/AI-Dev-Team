from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.runtime.team_runtime import TeamRuntime


class FakeRouter:
    """
    Deterministic router used by runtime integration tests.

    The router emulates the model layer without starting Ollama.
    This keeps the test fast and makes failures reproducible.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        task_type: str,
        think: bool = False,
    ) -> str:
        """Return deterministic model responses for each task type."""

        self.calls.append(
            {
                "task_type": task_type,
                "prompt": prompt,
                "think": think,
            }
        )

        if task_type == "management":
            return """
{
    "task_title": "Build authentication feature",
    "description": "Implement the requested authentication feature.",
    "capability": "coding",
    "priority": "high"
}
""".strip()

        raise AssertionError(
            "Unexpected model call during runtime "
            f"delegation test: {task_type}"
        )


class FakeOrchestrator:
    """
    Deterministic Orchestrator substitute.

    The real Orchestrator is already tested independently. These tests
    focus specifically on TeamRuntime's responsibility to create a task
    and delegate it using the Manager-selected capability.
    """

    def __init__(
        self,
        agent_manager,
    ) -> None:
        self.agent_manager = agent_manager
        self.calls: list[dict[str, Any]] = []

    def run_task_by_capability(
        self,
        task_id: str,
        capability: str,
        agent_manager,
    ) -> dict[str, Any]:
        """Record the delegation request and return deterministic evidence."""

        agent = agent_manager.find_agent_by_capability(
            capability
        )

        self.calls.append(
            {
                "task_id": task_id,
                "capability": capability,
                "agent": agent.name,
            }
        )

        return {
            "task_id": task_id,
            "status": "done",
            "attempts": 1,
            "decision": {
                "decision": "ACCEPT",
                "reason": "Deterministic delegation test.",
            },
        }


def build_runtime(
    tmp_path: Path,
) -> tuple[TeamRuntime, FakeRouter]:
    """
    Build a TeamRuntime with a deterministic model router.

    No Ollama process or external service is required.
    """

    state_manager = StateManager(
        tmp_path / "state"
    )

    task_manager = TaskManager(
        state_manager
    )

    router = FakeRouter()

    runtime = TeamRuntime(
        state_manager=state_manager,
        task_manager=task_manager,
        router=router,
        developer_workspace=str(
            tmp_path / "workspace"
        ),
    )

    return runtime, router


def test_runtime_delegates_manager_classification(
    tmp_path: Path,
) -> None:
    """Verify that Manager classification drives task delegation."""

    runtime, router = build_runtime(
        tmp_path
    )

    fake_orchestrator = FakeOrchestrator(
        runtime.agent_manager
    )

    runtime.orchestrator = fake_orchestrator

    result = runtime.run(
        "Build an authentication feature."
    )

    assert result["classification"] == {
        "task_title": "Build authentication feature",
        "description": (
            "Implement the requested "
            "authentication feature."
        ),
        "capability": "coding",
        "priority": "high",
    }

    task = result["task"]

    assert task is not None
    assert task["title"] == (
        "Build authentication feature"
    )
    assert task["description"] == (
        "Implement the requested "
        "authentication feature."
    )
    assert task["priority"] == "high"

    assert len(
        fake_orchestrator.calls
    ) == 1

    delegation = fake_orchestrator.calls[0]

    assert delegation["task_id"] == task["id"]
    assert delegation["capability"] == "coding"
    assert delegation["agent"] == "developer"

    assert result["result"]["status"] == "done"

    assert len(router.calls) == 1
    assert router.calls[0]["task_type"] == (
        "management"
    )


def test_runtime_normalizes_selected_capability(
    tmp_path: Path,
) -> None:
    """Verify that capability values are normalized before routing."""

    runtime, _ = build_runtime(
        tmp_path
    )

    runtime.manager.classify_task = (
        lambda instruction: {
            "task_title": "Architecture review",
            "description": (
                "Review the system architecture."
            ),
            "capability": "  ARCHITECTURE  ",
            "priority": "medium",
        }
    )

    fake_orchestrator = FakeOrchestrator(
        runtime.agent_manager
    )

    runtime.orchestrator = fake_orchestrator

    result = runtime.run(
        "Review the architecture."
    )

    assert result["result"]["status"] == "done"

    assert len(
        fake_orchestrator.calls
    ) == 1

    delegation = fake_orchestrator.calls[0]

    assert delegation["capability"] == (
        "architecture"
    )
    assert delegation["agent"] == "architect"


def test_runtime_rejects_empty_instruction(
    tmp_path: Path,
) -> None:
    """Verify that blank user instructions are rejected early."""

    runtime, _ = build_runtime(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="Instruction cannot be empty",
    ):
        runtime.run("   ")


@pytest.mark.parametrize(
    "missing_field",
    [
        "task_title",
        "description",
        "capability",
        "priority",
    ],
)
def test_runtime_rejects_incomplete_manager_classification(
    tmp_path: Path,
    missing_field: str,
) -> None:
    """Verify that incomplete Manager output cannot create a task."""

    runtime, _ = build_runtime(
        tmp_path
    )

    classification = {
        "task_title": "Example task",
        "description": "Example description.",
        "capability": "coding",
        "priority": "medium",
    }

    classification.pop(
        missing_field
    )

    runtime.manager.classify_task = (
        lambda instruction: classification
    )

    with pytest.raises(
        ValueError,
        match="Manager classification is missing fields",
    ):
        runtime.run(
            "Build something."
        )


def test_runtime_rejects_unknown_capability(
    tmp_path: Path,
) -> None:
    """
    Verify that an unsupported capability cannot silently select
    an unrelated specialist.
    """

    runtime, _ = build_runtime(
        tmp_path
    )

    runtime.manager.classify_task = (
        lambda instruction: {
            "task_title": "Unknown task",
            "description": "Unsupported capability.",
            "capability": "does_not_exist",
            "priority": "medium",
        }
    )

    fake_orchestrator = FakeOrchestrator(
        runtime.agent_manager
    )

    runtime.orchestrator = fake_orchestrator

    with pytest.raises(
        ValueError,
        match="No agent supports capability",
    ):
        runtime.run(
            "Perform an unsupported task."
        )

    assert fake_orchestrator.calls == []