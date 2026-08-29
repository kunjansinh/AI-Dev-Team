import json
from pathlib import Path

from app.agents.developer_agent import DeveloperAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager


class FakeDeveloperLLM:
    """Fake coding model for Developer tests."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        self.call_count += 1
        return self.response


def test_developer_generates_and_tests_code(
    tmp_path: Path,
) -> None:
    response = json.dumps(
        {
            "files": {
                "email_utils.py": (
                    "def is_valid_email(value):\n"
                    "    return '@' in value\n"
                ),
                "test_email_utils.py": (
                    "from email_utils import is_valid_email\n\n"
                    "def test_valid_email():\n"
                    "    assert is_valid_email('a@example.com')\n\n"
                    "def test_invalid_email():\n"
                    "    assert not is_valid_email('invalid')\n"
                ),
            }
        }
    )

    state_manager = StateManager(
        tmp_path / "state"
    )

    task_manager = TaskManager(
        state_manager
    )

    llm = FakeDeveloperLLM(response)

    developer = DeveloperAgent(
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm,
        workspace=tmp_path / "workspace",
    )

    task = task_manager.create_task(
        title="Email validator",
        description="Create an email validator.",
    )

    result = developer.execute(
        task["id"]
    )

    assert result["status"] == "awaiting_review"
    assert result["validation"]["status"] == "passed"
    assert result["validation"]["tests_passed"] == 2

    assert (
        tmp_path
        / "workspace"
        / "email_utils.py"
    ).exists()

    assert (
        tmp_path
        / "workspace"
        / "test_email_utils.py"
    ).exists()


def test_developer_reports_no_tests(
    tmp_path: Path,
) -> None:
    response = json.dumps(
        {
            "files": {
                "email_utils.py": (
                    "def is_valid_email(value):\n"
                    "    return '@' in value\n"
                )
            }
        }
    )

    state_manager = StateManager(
        tmp_path / "state"
    )

    task_manager = TaskManager(
        state_manager
    )

    llm = FakeDeveloperLLM(response)

    developer = DeveloperAgent(
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm,
        workspace=tmp_path / "workspace",
    )

    task = task_manager.create_task(
        title="Email validator",
        description="Create an email validator.",
    )

    result = developer.execute(
        task["id"]
    )

    assert result["status"] == "awaiting_review"
    assert result["validation"]["status"] == "no_tests"
    assert result["validation"]["tests_collected"] == 0


def test_developer_rejects_unsafe_path(
    tmp_path: Path,
) -> None:
    response = json.dumps(
        {
            "files": {
                "../outside.py": "print('unsafe')"
            }
        }
    )

    state_manager = StateManager(
        tmp_path / "state"
    )

    task_manager = TaskManager(
        state_manager
    )

    llm = FakeDeveloperLLM(response)

    developer = DeveloperAgent(
        state_manager=state_manager,
        task_manager=task_manager,
        llm_client=llm,
        workspace=tmp_path / "workspace",
    )

    task = task_manager.create_task(
        title="Unsafe task",
        description="Should not escape workspace.",
    )

    result = developer.execute(
        task["id"]
    )

    assert result["status"] == "error"
    assert result["validation"]["status"] == "error"