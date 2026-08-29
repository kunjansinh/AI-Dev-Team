from __future__ import annotations

from app.agents.architect_agent import ArchitectAgent
from app.agents.qa_agent import QAAgent
from app.agents.researcher_agent import ResearcherAgent
from app.agents.security_agent import SecurityAgent


class FakeStateManager:
    def __init__(self) -> None:
        self.agents = {}

    def load_agents(self):
        return dict(self.agents)

    def save_agents(self, agents):
        self.agents = dict(agents)

    def create_checkpoint(self, task_id, checkpoint):
        pass


class FakeTaskManager:
    def __init__(self) -> None:
        self.task = {
            "id": "TASK-TEST",
            "title": "Test specialist",
            "description": "Test specialist behavior.",
            "priority": "medium",
            "iteration": 0,
        }

    def get_task(self, task_id):
        if task_id == self.task["id"]:
            return dict(self.task)
        return None

    def assign_task(self, task_id, agent_name):
        self.task["assigned_to"] = agent_name

    def record_result(self, task_id, result, progress):
        self.task["result"] = result
        self.task["progress"] = progress
        return dict(self.task)

    def update_status(self, task_id, status):
        self.task["status"] = status
        return dict(self.task)

    def record_error(self, task_id, error):
        self.task["error"] = error


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt, think=False):
        return self.response


class FakeTestingTool:
    def run_pytest(self, workspace):
        return {
            "status": "passed",
            "exit_code": 0,
            "tests_collected": 1,
            "tests_passed": 1,
            "tests_failed": 0,
            "tests_skipped": 0,
        }


def make_dependencies():
    return FakeStateManager(), FakeTaskManager()


def test_architect_agent_has_correct_identity():
    state, tasks = make_dependencies()

    agent = ArchitectAgent(
        state,
        tasks,
        FakeLLM('{"summary": "ok"}'),
    )

    assert agent.name == "architect"
    assert agent.role == "Software Architect"


def test_researcher_agent_has_correct_identity():
    state, tasks = make_dependencies()

    agent = ResearcherAgent(
        state,
        tasks,
        FakeLLM('{"summary": "ok"}'),
    )

    assert agent.name == "researcher"
    assert agent.role == "Technical Researcher"


def test_qa_agent_has_correct_identity():
    state, tasks = make_dependencies()

    agent = QAAgent(
        state,
        tasks,
        FakeLLM('{"test_cases": []}'),
        testing_tool=FakeTestingTool(),
    )

    assert agent.name == "qa"
    assert agent.role == "Quality Assurance Engineer"


def test_security_agent_has_correct_identity():
    state, tasks = make_dependencies()

    agent = SecurityAgent(
        state,
        tasks,
        FakeLLM('{"risk_level": "low"}'),
    )

    assert agent.name == "security"
    assert agent.role == "Security Engineer"


def test_architect_agent_returns_structured_result():
    state, tasks = make_dependencies()

    agent = ArchitectAgent(
        state,
        tasks,
        FakeLLM(
            '{"summary": "simple architecture", '
            '"components": []}'
        ),
    )

    result = agent.execute("TASK-TEST")

    assert result["agent"] == "architect"
    assert result["status"] == "awaiting_review"
    assert result["architecture"]["summary"] == (
        "simple architecture"
    )


def test_researcher_agent_returns_structured_result():
    state, tasks = make_dependencies()

    agent = ResearcherAgent(
        state,
        tasks,
        FakeLLM(
            '{"summary": "research complete", '
            '"findings": []}'
        ),
    )

    result = agent.execute("TASK-TEST")

    assert result["agent"] == "researcher"
    assert result["research"]["summary"] == (
        "research complete"
    )


def test_qa_agent_runs_testing_tool():
    state, tasks = make_dependencies()

    agent = QAAgent(
        state,
        tasks,
        FakeLLM('{"test_cases": []}'),
        testing_tool=FakeTestingTool(),
    )

    result = agent.execute("TASK-TEST")

    assert result["agent"] == "qa"
    assert result["validation"]["status"] == "passed"
    assert result["validation"]["tests_passed"] == 1


def test_security_agent_returns_structured_result():
    state, tasks = make_dependencies()

    agent = SecurityAgent(
        state,
        tasks,
        FakeLLM(
            '{"risk_level": "low", '
            '"findings": []}'
        ),
    )

    result = agent.execute("TASK-TEST")

    assert result["agent"] == "security"
    assert result["security_review"]["risk_level"] == "low"