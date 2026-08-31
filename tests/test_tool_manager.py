from __future__ import annotations

import pytest

from app.core.permissions import PermissionManager
from app.core.tool_manager import ToolManager


def test_register_and_list_tools():
    manager = ToolManager()

    manager.register(
        "echo",
        "Return a value.",
        lambda value: value,
    )

    assert manager.list_tools() == ["echo"]


def test_duplicate_tool_registration_is_rejected():
    manager = ToolManager()

    manager.register(
        "echo",
        "Return a value.",
        lambda value: value,
    )

    with pytest.raises(ValueError):
        manager.register(
            "echo",
            "Duplicate.",
            lambda value: value,
        )


def test_permission_is_required():
    manager = ToolManager()

    manager.register(
        "run_tests",
        "Run tests.",
        lambda: "tests",
    )

    result = manager.execute(
        "researcher",
        "run_tests",
    )

    assert result["status"] == "error"
    assert result["error_type"] == "PermissionError"


def test_authorized_tool_executes():
    manager = ToolManager()

    manager.register(
        "read_file",
        "Read a file.",
        lambda path: f"read:{path}",
    )

    result = manager.execute(
        "developer",
        "read_file",
        path="example.py",
    )

    assert result["status"] == "success"
    assert result["result"] == "read:example.py"


def test_tool_errors_become_structured_results():
    manager = ToolManager()

    def failing_tool():
        raise RuntimeError("tool failed")

    manager.register(
        "read_file",
        "Read a file.",
        failing_tool,
    )

    result = manager.execute(
        "developer",
        "read_file",
    )

    assert result["status"] == "error"
    assert result["error"] == "tool failed"
    assert result["error_type"] == "RuntimeError"


def test_unknown_tool_is_rejected():
    manager = ToolManager()

    with pytest.raises(ValueError):
        manager.get("does_not_exist")


def test_can_execute_checks_registration_and_permission():
    manager = ToolManager()

    manager.register(
        "read_file",
        "Read a file.",
        lambda: "ok",
    )

    assert manager.can_execute(
        "developer",
        "read_file",
    )

    assert not manager.can_execute(
        "researcher",
        "create_file",
    )

    assert not manager.can_execute(
        "developer",
        "unknown",
    )


def test_tool_names_are_normalized():
    manager = ToolManager()

    manager.register(
        "  READ_FILE  ",
        "Read a file.",
        lambda: "ok",
    )

    assert manager.list_tools() == ["read_file"]

    result = manager.execute(
        "developer",
        " READ_FILE ",
    )

    assert result["status"] == "success"


def test_custom_permission_manager_is_used():
    permissions = PermissionManager()
    permissions.grant(
        "researcher",
        "custom_tool",
    )

    manager = ToolManager(
        permission_manager=permissions,
    )

    manager.register(
        "custom_tool",
        "Custom tool.",
        lambda: "custom",
    )

    result = manager.execute(
        "researcher",
        "custom_tool",
    )

    assert result["status"] == "success"
    assert result["result"] == "custom"
