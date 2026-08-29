import pytest

from app.core.agent_manager import AgentManager


class FakeAgent:
    """Simple fake agent for registry tests."""

    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture
def registry() -> AgentManager:
    manager = AgentManager()

    manager.register_agent(
        FakeAgent("architect"),
        ["architecture", "design"],
    )

    manager.register_agent(
        FakeAgent("developer"),
        ["coding", "implementation"],
    )

    manager.register_agent(
        FakeAgent("qa"),
        ["testing", "validation"],
    )

    return manager


def test_agent_can_be_registered(
    registry: AgentManager,
) -> None:
    assert registry.has_agent("developer")
    assert "developer" in registry.list_agents()


def test_agent_can_be_retrieved(
    registry: AgentManager,
) -> None:
    agent = registry.get_agent("developer")

    assert agent.name == "developer"


def test_capabilities_are_normalized(
    registry: AgentManager,
) -> None:
    capabilities = registry.get_capabilities("architect")

    assert capabilities == {
        "architecture",
        "design",
    }


def test_agent_can_be_found_by_capability(
    registry: AgentManager,
) -> None:
    agent = registry.find_agent_by_capability("coding")

    assert agent.name == "developer"


def test_capability_lookup_is_case_insensitive(
    registry: AgentManager,
) -> None:
    agent = registry.find_agent_by_capability(
        "ARCHITECTURE"
    )

    assert agent.name == "architect"


def test_multiple_agents_can_support_same_capability() -> None:
    manager = AgentManager()

    manager.register_agent(
        FakeAgent("developer"),
        ["coding"],
    )

    manager.register_agent(
        FakeAgent("architect"),
        ["coding", "architecture"],
    )

    matches = manager.find_agents_by_capability("coding")

    assert len(matches) == 2


def test_unknown_agent_is_rejected(
    registry: AgentManager,
) -> None:
    with pytest.raises(
        ValueError,
        match="Agent is not registered",
    ):
        registry.get_agent("unknown")


def test_unknown_capability_is_rejected(
    registry: AgentManager,
) -> None:
    with pytest.raises(
        ValueError,
        match="No agent supports capability",
    ):
        registry.find_agent_by_capability(
            "database_migration",
        )


def test_duplicate_agent_is_rejected() -> None:
    manager = AgentManager()

    manager.register_agent(
        FakeAgent("developer"),
        ["coding"],
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        manager.register_agent(
            FakeAgent("developer"),
            ["implementation"],
        )


def test_agent_without_capability_is_rejected() -> None:
    manager = AgentManager()

    with pytest.raises(
        ValueError,
        match="at least one capability",
    ):
        manager.register_agent(
            FakeAgent("developer"),
            [],
        )


def test_agent_can_be_unregistered(
    registry: AgentManager,
) -> None:
    registry.unregister_agent("developer")

    assert not registry.has_agent("developer")

    with pytest.raises(
        ValueError,
        match="Agent is not registered",
    ):
        registry.get_agent("developer")


def test_team_description_is_available(
    registry: AgentManager,
) -> None:
    team = registry.describe_team()

    assert team["architect"] == [
        "architecture",
        "design",
    ]

    assert team["developer"] == [
        "coding",
        "implementation",
    ]