from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDefinition:
    """Description of an AI model."""

    name: str
    purpose: str
    context_size: int
    preferred_for: tuple[str, ...]
    provider: str = "ollama"


class ModelRegistry:
    """Registry of available AI models."""

    def __init__(self) -> None:
        self._models: dict[str, ModelDefinition] = {}

        # Local Ollama models
        self.register(
            ModelDefinition(
                name="qwen3:1.7b",
                purpose="fast general-purpose management and reasoning",
                context_size=4096,
                preferred_for=(
                    "management",
                    "planning",
                    "research",
                    "qa",
                    "security",
                ),
                provider="ollama",
            )
        )

        self.register(
            ModelDefinition(
                name="qwen3:4b",
                purpose="heavier reasoning and coding work",
                context_size=4096,
                preferred_for=(
                    "coding",
                    "complex_analysis",
                    "architecture",
                ),
                provider="ollama",
            )
        )

        # OpenRouter free model router
        self.register(
            ModelDefinition(
                name="openrouter/free",
                purpose="free cloud model routing and fallback",
                context_size=4096,
                preferred_for=(),
                provider="openrouter",
            )
        )

    def register(self, model: ModelDefinition) -> None:
        """Register a model."""

        if model.name in self._models:
            raise ValueError(
                f"Model already registered: {model.name}"
            )

        self._models[model.name] = model

    def get(self, model_name: str) -> ModelDefinition:
        """Return a registered model."""

        model = self._models.get(model_name)

        if model is None:
            raise ValueError(
                f"Model is not registered: {model_name}"
            )

        return model

    def list_models(self) -> list[str]:
        """Return all registered model names."""

        return list(self._models.keys())

    def find_for_task(self, task_type: str) -> list[ModelDefinition]:
        """Find models preferred for a task type."""

        normalized = task_type.strip().lower()

        return [
            model
            for model in self._models.values()
            if normalized in model.preferred_for
        ]

    def default_for(self, task_type: str) -> ModelDefinition:
        """Return the preferred model for a task."""

        matches = self.find_for_task(task_type)

        if not matches:
            return self.get("qwen3:1.7b")

        return matches[0]