import pytest

from app.config.settings import settings
from app.core.permissions import PermissionManager
from app.tools.llm.model_registry import ModelRegistry


def test_manager_model_is_configured() -> None:
    assert settings.manager_model == "qwen3:1.7b"


def test_model_registry_contains_expected_models() -> None:
    registry = ModelRegistry()

    assert "qwen3:1.7b" in registry.list_models()
    assert "qwen3:4b" in registry.list_models()


def test_model_registry_selects_fast_manager_model() -> None:
    registry = ModelRegistry()

    model = registry.default_for("management")

    assert model.name == "qwen3:1.7b"


def test_model_registry_selects_heavier_model_for_coding() -> None:
    registry = ModelRegistry()

    model = registry.default_for("coding")

    assert model.name == "qwen3:4b"


def test_manager_has_safe_permissions() -> None:
    permissions = PermissionManager()

    assert permissions.can(
        "manager",
        "read_file",
    )

    assert not permissions.can(
        "manager",
        "run_tests",
    )


def test_developer_can_run_tests() -> None:
    permissions = PermissionManager()

    assert permissions.can(
        "developer",
        "run_tests",
    )


def test_unauthorized_tool_is_rejected() -> None:
    permissions = PermissionManager()

    with pytest.raises(PermissionError):
        permissions.require(
            "researcher",
            "modify_file",
        )   