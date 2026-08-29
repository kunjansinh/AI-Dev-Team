from pathlib import Path

from app.agents.manager_agent import ManagerAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class FakeLLM:
    def __init__(self) -> None:
        self.response = "{}"
        self.last_prompt = ""

    def generate(self, prompt: str, think: bool = False) -> str:
        self.last_prompt = prompt
        return self.response


def test_manager_review_prompt_is_requirement_first(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    llm = FakeLLM()
    manager = ManagerAgent(state, tasks, llm)

    task = tasks.create_task(
        title="Email validation",
        description=(
            "Implement is_valid_email and include automated pytest tests."
        ),
    )

    llm.response = (
        '{"decision":"ACCEPT","reason":"Explicit requirements are met '
        'and validation passed.","missing_evidence":[],'
        '"next_action":"Proceed."}'
    )

    manager.review_task(
        task["id"],
        {
            "validation": {
                "status": "passed",
                "tests_collected": 15,
                "tests_passed": 15,
                "tests_failed": 0,
                "exit_code": 0,
            }
        },
    )

    assert "Judge the implementation against the TASK's explicit requirements first." in llm.last_prompt
    assert "Do not invent additional requirements" in llm.last_prompt
    assert "Do NOT reject working code merely because additional edge cases" in llm.last_prompt


def test_manager_review_prompt_requires_concrete_rework_reason(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    llm = FakeLLM()
    manager = ManagerAgent(state, tasks, llm)

    task = tasks.create_task(
        title="Checkout",
        description="Implement checkout and make all automated tests pass.",
    )

    llm.response = (
        '{"decision":"REWORK","reason":"Two required tests fail.",'
        '"missing_evidence":["Passing payment test"],'
        '"next_action":"Fix payment handling and rerun tests."}'
    )

    manager.review_task(
        task["id"],
        {"tests_passed": 8, "tests_failed": 2},
    )

    assert "For REWORK, state exactly what must change and how it can be verified." in llm.last_prompt
