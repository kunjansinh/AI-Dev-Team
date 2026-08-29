from __future__ import annotations

from app.core.agent_manager import AgentManager


class FakeAgent:
    def __init__(self, name: str) -> None:
        self.name = name


def test_agent_manager_can_register_specialist_capabilities() -> None:
    manager = AgentManager()

    architect = FakeAgent("architect")
    researcher = FakeAgent("researcher")
    qa = FakeAgent("qa")
    security = FakeAgent("security")

    manager.register_agent(
        architect,
        {
            "architecture",
            "system_design",
            "technology_selection",
        },
    )

    manager.register_agent(
        researcher,
        {
            "requirements_analysis",
            "research",
            "technology_research",
        },
    )

    manager.register_agent(
        qa,
        {
            "quality_assurance",
            "testing",
            "validation",
        },
    )

    manager.register_agent(
        security,
        {
            "security",
            "threat_modeling",
            "vulnerability_analysis",
        },
    )

    assert (
        manager.find_agent_by_capability(
            "architecture"
        ).name
        == "architect"
    )

    assert (
        manager.find_agent_by_capability(
            "research"
        ).name
        == "researcher"
    )

    assert (
        manager.find_agent_by_capability(
            "testing"
        ).name
        == "qa"
    )

    assert (
        manager.find_agent_by_capability(
            "security"
        ).name
        == "security"
    )


def test_agent_manager_capability_lookup_is_case_insensitive() -> None:
    manager = AgentManager()

    architect = FakeAgent("architect")

    manager.register_agent(
        architect,
        {
            "architecture",
        },
    )

    assert (
        manager.find_agent_by_capability(
            "ARCHITECTURE"
        ).name
        == "architect"
    )