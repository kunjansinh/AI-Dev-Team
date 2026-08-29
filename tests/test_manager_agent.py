from pathlib import Path

import pytest

from app.agents.manager_agent import ManagerAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class FakeManagerLLM:
    """Fake LLM used to test Manager behavior without Ollama."""

    def __init__(self) -> None:
        self.responses: list[str] = ["{}"]
        self.last_prompt: str | None = None
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Return queued fake responses."""

        self.last_prompt = prompt
        self.call_count += 1

        if self.responses:
            return self.responses.pop(0)

        return "{}"


@pytest.fixture
def manager_components(
    tmp_path: Path,
) -> tuple[
    StateManager,
    TaskManager,
    FakeManagerLLM,
    ManagerAgent,
]:
    """Create isolated Manager dependencies for each test."""

    state_manager = StateManager(tmp_path / "state")
    task_manager = TaskManager(state_manager)
    llm = FakeManagerLLM()

    manager = ManagerAgent(
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm,
    )

    return (
        state_manager,
        task_manager,
        llm,
        manager,
    )


def test_manager_registers_correctly(
    manager_components,
) -> None:
    state_manager, _, _, _ = manager_components

    agents = state_manager.load_agents()

    assert "manager" in agents
    assert agents["manager"]["role"] == "Technical Manager"
    assert agents["manager"]["status"] == "available"


def test_manager_prompt_contains_leadership_rules(
    manager_components,
) -> None:
    _, _, _, manager = manager_components

    prompt = manager.build_manager_prompt(
        "Evaluate this architecture."
    )

    assert "You are NOT a yes-man." in prompt
    assert "No evidence = not complete." in prompt
    assert "technical leader" in prompt.lower()


def test_manager_can_create_task(
    manager_components,
) -> None:
    _, task_manager, _, manager = manager_components

    task = manager.create_task_from_instruction(
        title="Design database",
        description="Design the initial PostgreSQL schema.",
        priority="high",
        assigned_to="architect",
    )

    saved_task = task_manager.get_task(task["id"])

    assert saved_task is not None
    assert saved_task["title"] == "Design database"
    assert saved_task["priority"] == "high"
    assert saved_task["assigned_to"] == "architect"


def test_manager_accepts_valid_review(
    manager_components,
) -> None:
    _, task_manager, llm, manager = manager_components

    task = task_manager.create_task(
        title="Build login API",
        description="Implement login.",
    )

    llm.responses = [
        """
{
    "decision": "ACCEPT",
    "reason": "All required tests passed.",
    "missing_evidence": [],
    "next_action": "Proceed to next task."
}
""".strip()
    ]

    result = manager.review_task(
        task["id"],
        {
            "tests_passed": 10,
            "tests_failed": 0,
            "security_issues": 0,
        },
    )

    updated = task_manager.get_task(task["id"])

    assert result["decision"] == "ACCEPT"
    assert updated is not None
    assert updated["status"] == "done"


def test_manager_requests_rework(
    manager_components,
) -> None:
    _, task_manager, llm, manager = manager_components

    task = task_manager.create_task(
        title="Build checkout",
        description="Implement checkout.",
    )

    llm.responses = [
        """
{
    "decision": "REWORK",
    "reason": "Two required tests are failing.",
    "missing_evidence": ["Successful payment test"],
    "next_action": "Fix payment handling and rerun tests."
}
""".strip()
    ]

    result = manager.review_task(
        task["id"],
        {
            "tests_passed": 8,
            "tests_failed": 2,
        },
    )

    updated = task_manager.get_task(task["id"])

    assert result["decision"] == "REWORK"
    assert updated is not None
    assert updated["status"] == "rework"


def test_manager_can_block_task(
    manager_components,
) -> None:
    _, task_manager, llm, manager = manager_components

    task = task_manager.create_task(
        title="Deploy application",
        description="Deploy to production.",
    )

    llm.responses = [
        """
{
    "decision": "BLOCK",
    "reason": "Production credentials are unavailable.",
    "missing_evidence": ["Valid deployment credentials"],
    "next_action": "Provide credentials through the approved secure process."
}
""".strip()
    ]

    result = manager.review_task(
        task["id"],
        {},
    )

    updated = task_manager.get_task(task["id"])

    assert result["decision"] == "BLOCK"
    assert updated is not None
    assert updated["status"] == "blocked"
    assert updated["error"] == (
        "Production credentials are unavailable."
    )


def test_manager_rejects_invalid_decision(
    manager_components,
) -> None:
    _, task_manager, llm, manager = manager_components

    task = task_manager.create_task(
        title="Test feature",
        description="Test feature implementation.",
    )

    llm.responses = [
        """
{
    "decision": "MAYBE",
    "reason": "Unclear."
}
""".strip()
    ]

    with pytest.raises(
        ValueError,
        match="Invalid Manager decision",
    ):
        manager.review_task(
            task["id"],
            {},
        )


def test_manager_rejects_invalid_json(
    manager_components,
) -> None:
    _, _, llm, manager = manager_components

    llm.responses = [
        "This is not JSON.",
        "Still not JSON.",
    ]

    with pytest.raises(
        ValueError,
        match="failed to return valid JSON",
    ):
        manager.evaluate_proposal(
            "Use a complicated architecture."
        )

    assert llm.call_count == 2


def test_manager_accepts_json_inside_markdown_fence(
    manager_components,
) -> None:
    _, _, llm, manager = manager_components

    llm.responses = [
        """```json
{
    "decision": "APPROVE",
    "reason": "The proposal is reasonable.",
    "risks": [],
    "alternatives": [],
    "recommended_action": "Proceed."
}
```"""
    ]

    result = manager.evaluate_proposal(
        "Use PostgreSQL for the application."
    )

    assert result["decision"] == "APPROVE"
    assert llm.call_count == 1


def test_manager_retries_after_invalid_json(
    manager_components,
) -> None:
    _, _, llm, manager = manager_components

    llm.responses = [
        "This is not JSON.",
        """
{
    "decision": "REJECT",
    "reason": "The design is too complex.",
    "risks": ["Complexity"],
    "alternatives": ["Use a simpler architecture."],
    "recommended_action": "Simplify the design."
}
""".strip(),
    ]

    result = manager.evaluate_proposal(
        "Use ten microservices for a tiny application."
    )

    assert result["decision"] == "REJECT"
    assert llm.call_count == 2


def test_manager_fails_safely_after_retry(
    manager_components,
) -> None:
    _, _, llm, manager = manager_components

    llm.responses = [
        "Not JSON",
        "Still not JSON",
    ]

    with pytest.raises(
        ValueError,
        match="failed to return valid JSON",
    ):
        manager.evaluate_proposal(
            "Use a complicated architecture."
        )

    assert llm.call_count == 2


def test_manager_does_not_accept_json_array(
    manager_components,
) -> None:
    _, _, llm, manager = manager_components

    llm.responses = [
        "[]",
        "[]",
    ]

    with pytest.raises(
        ValueError,
        match="failed to return valid JSON",
    ):
        manager.evaluate_proposal(
            "Evaluate this proposal."
        )

    assert llm.call_count == 2