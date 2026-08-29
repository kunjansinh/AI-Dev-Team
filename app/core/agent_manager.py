from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRegistration:
    """Metadata about a registered agent."""

    agent: Any
    capabilities: set[str] = field(default_factory=set)


class AgentManager:
    """
    Registry and capability directory for development-team agents.

    The AgentManager does not execute agents.
    It only knows which agents exist and what they can do.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentRegistration] = {}

    def register_agent(
        self,
        agent: Any,
        capabilities: list[str] | set[str],
    ) -> None:
        """Register an agent and its capabilities."""

        name = getattr(agent, "name", None)

        if not name:
            raise ValueError("Agent must have a name.")

        if name in self._agents:
            raise ValueError(
                f"Agent is already registered: {name}"
            )

        normalized_capabilities = {
            capability.strip().lower()
            for capability in capabilities
            if capability.strip()
        }

        if not normalized_capabilities:
            raise ValueError(
                f"Agent must have at least one capability: {name}"
            )

        self._agents[name] = AgentRegistration(
            agent=agent,
            capabilities=normalized_capabilities,
        )

    def unregister_agent(self, agent_name: str) -> None:
        """Remove a registered agent."""

        if agent_name not in self._agents:
            raise ValueError(
                f"Agent is not registered: {agent_name}"
            )

        del self._agents[agent_name]

    def get_agent(self, agent_name: str) -> Any:
        """Return an agent by name."""

        registration = self._agents.get(agent_name)

        if registration is None:
            raise ValueError(
                f"Agent is not registered: {agent_name}"
            )

        return registration.agent

    def get_capabilities(self, agent_name: str) -> set[str]:
        """Return the capabilities of a registered agent."""

        registration = self._agents.get(agent_name)

        if registration is None:
            raise ValueError(
                f"Agent is not registered: {agent_name}"
            )

        return set(registration.capabilities)

    def find_agents_by_capability(
        self,
        capability: str,
    ) -> list[Any]:
        """Return all agents that support a capability."""

        normalized_capability = capability.strip().lower()

        if not normalized_capability:
            raise ValueError("Capability cannot be empty.")

        return [
            registration.agent
            for registration in self._agents.values()
            if normalized_capability in registration.capabilities
        ]

    def find_agent_by_capability(
        self,
        capability: str,
    ) -> Any:
        """
        Return one agent for a capability.

        For now, the first registered matching agent is selected.
        Later the Orchestrator can add availability, workload,
        model cost, and health-based selection.
        """

        matches = self.find_agents_by_capability(capability)

        if not matches:
            raise ValueError(
                f"No agent supports capability: {capability}"
            )

        return matches[0]

    def has_agent(self, agent_name: str) -> bool:
        """Check whether an agent is registered."""

        return agent_name in self._agents

    def list_agents(self) -> list[str]:
        """Return all registered agent names."""

        return list(self._agents.keys())

    def describe_team(self) -> dict[str, list[str]]:
        """Return a simple agent-to-capability map."""

        return {
            name: sorted(registration.capabilities)
            for name, registration in self._agents.items()
        }