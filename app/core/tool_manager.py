from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.permissions import PermissionManager


@dataclass(frozen=True)
class ToolDefinition:
    """Definition of an executable team tool."""

    name: str
    description: str
    handler: Callable[..., Any]


class ToolManager:
    """Central execution gateway for agent tools."""

    def __init__(
        self,
        permission_manager: PermissionManager | None = None,
    ) -> None:
        self.permission_manager = (
            permission_manager or PermissionManager()
        )
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register an executable tool."""

        normalized = self._normalize_name(name)

        if normalized in self._tools:
            raise ValueError(
                f"Tool already registered: {normalized}"
            )

        if not callable(handler):
            raise TypeError(
                f"Tool handler must be callable: {normalized}"
            )

        self._tools[normalized] = ToolDefinition(
            name=normalized,
            description=description.strip(),
            handler=handler,
        )

    def unregister(self, name: str) -> None:
        """Remove a registered tool."""

        normalized = self._normalize_name(name)

        if normalized not in self._tools:
            raise ValueError(
                f"Tool is not registered: {normalized}"
            )

        del self._tools[normalized]

    def get(self, name: str) -> ToolDefinition:
        """Return a registered tool."""

        normalized = self._normalize_name(name)

        tool = self._tools.get(normalized)

        if tool is None:
            raise ValueError(
                f"Tool is not registered: {normalized}"
            )

        return tool

    def list_tools(self) -> list[str]:
        """Return registered tool names."""

        return list(self._tools.keys())

    def describe_tools(self) -> list[dict[str, str]]:
        """Return metadata for all registered tools."""

        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]

    def can_execute(
        self,
        agent_name: str,
        tool_name: str,
    ) -> bool:
        """Return whether an agent may execute a tool."""

        normalized = self._normalize_name(tool_name)

        if normalized not in self._tools:
            return False

        return self.permission_manager.can(
            agent_name,
            normalized,
        )

    def execute(
        self,
        agent_name: str,
        tool_name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute a tool through the controlled gateway.

        Permission checks and tool failures are returned as
        structured execution results.
        """

        normalized = self._normalize_name(tool_name)

        try:
            tool = self.get(normalized)

            self.permission_manager.require(
                agent_name,
                normalized,
            )

            result = tool.handler(**kwargs)

            return {
                "status": "success",
                "tool": normalized,
                "agent": agent_name,
                "result": result,
            }

        except Exception as exc:
            return {
                "status": "error",
                "tool": normalized,
                "agent": agent_name,
                "result": None,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    def require_tool(self, name: str) -> ToolDefinition:
        """Return a tool or raise an informative error."""

        return self.get(name)

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize and validate a tool name."""

        if not isinstance(name, str):
            raise TypeError("Tool name must be a string.")

        normalized = name.strip().lower()

        if not normalized:
            raise ValueError("Tool name cannot be empty.")

        return normalized
