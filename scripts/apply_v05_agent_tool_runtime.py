
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


developer = ROOT / "app/agents/developer_agent.py"

patch_text(
    developer,
    '        self.tool_manager = tool_manager\n',
    '        self.tool_manager = tool_manager\n'
    '        self._tool_execution_log: list[dict[str, Any]] = []\n',
)

patch_text(
    developer,
    '        self._update_agent_status("working")\n\n'
    '        prompt = self._build_developer_prompt(task)\n',
    '        self._update_agent_status("working")\n'
    '        self._tool_execution_log = []\n\n'
    '        prompt = self._build_developer_prompt(task)\n',
)

patch_text(
    developer,
    '''                "written_files": written_files,
                "validation": validation,
            }''',
    '''                "written_files": written_files,
                "validation": validation,
                "tool_calls": list(self._tool_execution_log),
            }''',
)

patch_text(
    developer,
    '''                "written_files": [],
                "validation": {
                    "status": "error",''',
    '''                "written_files": [],
                "tool_calls": list(self._tool_execution_log),
                "validation": {
                    "status": "error",''',
)

patch_text(
    developer,
    '''        result = self.tool_manager.execute(
            self.name,
            tool_name,
            relative_path=relative_path,
            content=content,
        )

        if result["status"] != "success":''',
    '''        result = self.tool_manager.execute(
            self.name,
            tool_name,
            relative_path=relative_path,
            content=content,
        )
        self._tool_execution_log.append(result)

        if result["status"] != "success":''',
)

patch_text(
    developer,
    '''        result = self.tool_manager.execute(
            self.name,
            "run_tests",
        )

        if result["status"] != "success":''',
    '''        result = self.tool_manager.execute(
            self.name,
            "run_tests",
        )
        self._tool_execution_log.append(result)

        if result["status"] != "success":''',
)

test = ROOT / "tests/test_agent_tool_runtime_loop.py"
test.write_text('from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom app.agents.developer_agent import DeveloperAgent\nfrom app.core.state_manager import StateManager\nfrom app.core.task_manager import TaskManager\nfrom app.tools.workspace_registry import create_workspace_tool_manager\n\n\nclass FakeDeveloperLLM:\n    def generate(self, prompt: str, think: bool = False) -> str:\n        return \'{"files": {"hello.py": "def hello():\\\\n    return \\\\\'hello\\\\\'\\\\n", "test_hello.py": "from hello import hello\\\\n\\\\ndef test_hello():\\\\n    assert hello() == \\\\\'hello\\\\\'\\\\n"}}\'\n\n\ndef test_developer_executes_through_tool_runtime(tmp_path: Path) -> None:\n    state = StateManager(tmp_path / "state")\n    tasks = TaskManager(state)\n    workspace = tmp_path / "workspace"\n    tools = create_workspace_tool_manager(workspace)\n\n    task = tasks.create_task(\n        title="Create hello helper",\n        description="Create a hello function and a pytest test.",\n        priority="normal",\n    )\n\n    agent = DeveloperAgent(\n        state_manager=state,\n        task_manager=tasks,\n        llm_client=FakeDeveloperLLM(),\n        workspace=workspace,\n        tool_manager=tools,\n    )\n\n    result = agent.execute(task["id"])\n\n    assert result["status"] == "awaiting_review"\n    assert result["validation"]["status"] == "passed"\n    assert result["validation"]["tests_passed"] == 1\n\n    tool_calls = result["tool_calls"]\n    assert [call["tool"] for call in tool_calls] == [\n        "create_file",\n        "create_file",\n        "run_tests",\n    ]\n    assert all(call["status"] == "success" for call in tool_calls)\n    assert (workspace / "hello.py").exists()\n    assert (workspace / "test_hello.py").exists()\n\n\ndef test_developer_tool_evidence_is_returned_to_runtime(tmp_path: Path) -> None:\n    state = StateManager(tmp_path / "state")\n    tasks = TaskManager(state)\n    workspace = tmp_path / "workspace"\n    tools = create_workspace_tool_manager(workspace)\n\n    task = tasks.create_task(\n        title="Create hello helper",\n        description="Create a hello function and a pytest test.",\n        priority="normal",\n    )\n\n    agent = DeveloperAgent(\n        state_manager=state,\n        task_manager=tasks,\n        llm_client=FakeDeveloperLLM(),\n        workspace=workspace,\n        tool_manager=tools,\n    )\n\n    result = agent.execute(task["id"])\n\n    assert "tool_calls" in result\n    assert result["tool_calls"][-1]["tool"] == "run_tests"\n    assert result["tool_calls"][-1]["result"]["status"] == "passed"\n', encoding="utf-8")

print("V0.5 Agent -> Tool -> Runtime execution loop applied.")
print("Next: python -m pytest -q")
