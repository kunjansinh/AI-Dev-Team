from __future__ import annotations

from pathlib import Path

from app.agents.developer_agent import DeveloperAgent
from app.core.state_manager import StateManager
from app.core.task_manager import TaskManager
from app.tools.workspace_registry import create_workspace_tool_manager


class FakeDeveloperLLM:
    def generate(self, prompt: str, think: bool = False) -> str:
        return """{"files": {"hello.py": "def hello():\\n    return 'hello'\\n", "test_hello.py": "from hello import hello\\n\\ndef test_hello():\\n    assert hello() == 'hello'\\n"}}"""


def test_developer_executes_through_tool_runtime(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    workspace = tmp_path / "workspace"
    tools = create_workspace_tool_manager(workspace)

    task = tasks.create_task(
        title="Create hello helper",
        description="Create a hello function and a pytest test.",
        priority="normal",
    )

    agent = DeveloperAgent(
        state_manager=state,
        task_manager=tasks,
        llm_client=FakeDeveloperLLM(),
        workspace=workspace,
        tool_manager=tools,
    )

    result = agent.execute(task["id"])

    assert result["status"] == "awaiting_review"
    assert result["validation"]["status"] == "passed"
    assert result["validation"]["tests_passed"] == 1

    tool_calls = result["tool_calls"]
    assert [call["tool"] for call in tool_calls] == [
        "create_file",
        "create_file",
        "run_tests",
    ]
    assert all(call["status"] == "success" for call in tool_calls)
    assert (workspace / "hello.py").exists()
    assert (workspace / "test_hello.py").exists()


def test_developer_tool_evidence_is_returned_to_runtime(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state")
    tasks = TaskManager(state)
    workspace = tmp_path / "workspace"
    tools = create_workspace_tool_manager(workspace)

    task = tasks.create_task(
        title="Create hello helper",
        description="Create a hello function and a pytest test.",
        priority="normal",
    )

    agent = DeveloperAgent(
        state_manager=state,
        task_manager=tasks,
        llm_client=FakeDeveloperLLM(),
        workspace=workspace,
        tool_manager=tools,
    )

    result = agent.execute(task["id"])

    assert "tool_calls" in result
    assert result["tool_calls"][-1]["tool"] == "run_tests"
    assert result["tool_calls"][-1]["result"]["status"] == "passed"
