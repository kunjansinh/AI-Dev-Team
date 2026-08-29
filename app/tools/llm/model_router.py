from __future__ import annotations

from app.config.settings import settings
from app.tools.llm.model_registry import ModelDefinition, ModelRegistry
from app.tools.llm.ollama_client import OllamaClient
from app.tools.llm.openrouter_client import OpenRouterClient


class ModelRouter:
    """Routes AI requests between local Ollama and OpenRouter."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.registry = registry or ModelRegistry()

    def select_model(self, task_type: str) -> ModelDefinition:
        """Select the best registered model for a task."""

        return self.registry.default_for(task_type)

    def generate(
        self,
        prompt: str,
        task_type: str,
        think: bool = False,
    ) -> str:
        """
        Generate a response using the preferred model.

        If the local Ollama model fails and OpenRouter is enabled,
        automatically fall back to the OpenRouter free model.
        """

        model = self.select_model(task_type)

        try:
            return self._generate_with_model(
                model=model,
                prompt=prompt,
                think=think,
            )

        except Exception as local_error:
            if (
                model.provider == "ollama"
                and settings.openrouter_enabled
            ):
                fallback_model = self.registry.get(
                    settings.openrouter_model
                )

                try:
                    return self._generate_with_model(
                        model=fallback_model,
                        prompt=prompt,
                        think=think,
                    )
                except Exception as fallback_error:
                    raise RuntimeError(
                        "Both the primary model and OpenRouter "
                        "fallback failed."
                    ) from fallback_error

            raise local_error

    def _generate_with_model(
        self,
        model: ModelDefinition,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Generate a response using a specific model."""

        if model.provider == "ollama":
            client = OllamaClient(
                model=model.name,
                timeout=settings.ollama_timeout,
            )

            return client.generate(
                prompt,
                think=think,
            )

        if model.provider == "openrouter":
            client = OpenRouterClient(
                model=model.name,
                timeout=settings.openrouter_timeout,
            )

            return client.generate(
                prompt,
                think=think,
            )

        raise ValueError(
            f"Unsupported model provider: {model.provider}"
        )

class RoutedAgentClient:
    """LLM client adapter that routes an agent's requests automatically."""

    def __init__(
        self,
        router: ModelRouter,
        task_type: str,
    ) -> None:
        self.router = router
        self.task_type = task_type

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Generate a response using the router for this agent's task type."""

        return self.router.generate(
            prompt=prompt,
            task_type=self.task_type,
            think=think,
        )