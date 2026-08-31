from __future__ import annotations


class PermissionManager:
    """Controls which tools each agent is allowed to use."""

    DEFAULT_PERMISSIONS = {
        "manager": {
            "read_file",
            "list_files",
            "create_task",
            "review_task",
        },
        "architect": {
            "read_file",
            "list_files",
            "create_file",
        },
        "researcher": {
            "read_file",
            "list_files",
        },
        "developer": {
            "read_file",
            "list_files",
            "create_file",
            "modify_file",
            "run_tests",
            "git_diff",
            "run_command",
        },
        "qa": {
            "read_file",
            "list_files",
            "run_tests",
        },
        "security": {
            "read_file",
            "list_files",
            "run_tests",
        },
    }

    def __init__(self) -> None:
        self._permissions = {
            agent: set(tools)
            for agent, tools in self.DEFAULT_PERMISSIONS.items()
        }

    def can(self, agent_name: str, tool_name: str) -> bool:
        return tool_name in self._permissions.get(
            agent_name,
            set(),
        )

    def require(
        self,
        agent_name: str,
        tool_name: str,
    ) -> None:
        if not self.can(agent_name, tool_name):
            raise PermissionError(
                f"Agent '{agent_name}' is not allowed "
                f"to use tool '{tool_name}'."
            )

    def grant(
        self,
        agent_name: str,
        tool_name: str,
    ) -> None:
        self._permissions.setdefault(
            agent_name,
            set(),
        ).add(tool_name)

    def revoke(
        self,
        agent_name: str,
        tool_name: str,
    ) -> None:
        self._permissions.setdefault(
            agent_name,
            set(),
        ).discard(tool_name)

    def list_permissions(
        self,
        agent_name: str,
    ) -> set[str]:
        return set(
            self._permissions.get(
                agent_name,
                set(),
            )
        )