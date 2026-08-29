from types import SimpleNamespace

import pytest

from app.tools.llm.model_registry import ModelDefinition, ModelRegistry
from app.tools.llm.model_router import ModelRouter


def test_management_selects_fast_local_model():
    router = ModelRouter()

    model = router.select_model("management")

    assert model.name == "qwen3:1.7b"
    assert model.provider == "ollama"


def test_coding_selects_heavier_local_model():
    router = ModelRouter()

    model = router.select_model("coding")

    assert model.name == "qwen3:4b"
    assert model.provider == "ollama"


def test_unknown_task_uses_default_model():
    router = ModelRouter()

    model = router.select_model("unknown_task")

    assert model.name == "qwen3:1.7b"
    assert model.provider == "ollama"


def test_openrouter_is_registered():
    registry = ModelRegistry()

    model = registry.get("openrouter/free")

    assert model.name == "openrouter/free"
    assert model.provider == "openrouter"


def test_router_uses_selected_model():
    router = ModelRouter()

    calls = []

    def fake_generate(model, prompt, think=False):
        calls.append((model.name, prompt, think))
        return "local response"

    router._generate_with_model = fake_generate

    result = router.generate(
        "Hello",
        "management",
        think=True,
    )

    assert result == "local response"
    assert calls == [
        ("qwen3:1.7b", "Hello", True)
    ]


def test_router_falls_back_to_openrouter_when_local_fails():
    router = ModelRouter()

    calls = []

    def fake_generate(model, prompt, think=False):
        calls.append(model.name)

        if model.provider == "ollama":
            raise RuntimeError("Ollama unavailable")

        return "OpenRouter response"

    router._generate_with_model = fake_generate

    result = router.generate(
        "Solve this problem",
        "coding",
    )

    assert result == "OpenRouter response"
    assert calls == [
        "qwen3:4b",
        "openrouter/free",
    ]


def test_router_does_not_fallback_when_openrouter_disabled(
    monkeypatch,
):
    router = ModelRouter()

    monkeypatch.setattr(
        "app.tools.llm.model_router.settings",
        SimpleNamespace(
            openrouter_enabled=False,
            openrouter_model="openrouter/free",
            ollama_timeout=600,
            openrouter_timeout=120,
        ),
    )

    def fake_generate(model, prompt, think=False):
        raise RuntimeError("Ollama unavailable")

    router._generate_with_model = fake_generate

    with pytest.raises(RuntimeError, match="Ollama unavailable"):
        router.generate(
            "Test prompt",
            "management",
        )


def test_router_reports_when_both_models_fail():
    router = ModelRouter()

    def fake_generate(model, prompt, think=False):
        raise RuntimeError(
            f"{model.name} unavailable"
        )

    router._generate_with_model = fake_generate

    with pytest.raises(
        RuntimeError,
        match="Both the primary model and OpenRouter fallback failed",
    ):
        router.generate(
            "Test prompt",
            "coding",
        )


def test_unsupported_provider_is_rejected():
    router = ModelRouter()

    unsupported_model = ModelDefinition(
        name="unsupported-model",
        purpose="test model",
        context_size=4096,
        preferred_for=(),
        provider="unknown",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported model provider",
    ):
        router._generate_with_model(
            model=unsupported_model,
            prompt="Test prompt",
        )