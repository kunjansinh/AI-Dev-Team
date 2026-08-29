from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application-wide configuration."""

    # Ollama
    ollama_url: str = "http://localhost:11434"
    manager_model: str = "qwen3:1.7b"
    default_model: str = "qwen3:1.7b"
    heavy_model: str = "qwen3:4b"
    ollama_timeout: int = 600

    # OpenRouter
    openrouter_model: str = "openrouter/free"
    openrouter_timeout: int = 120
    openrouter_enabled: bool = True

    # Task execution
    max_task_iterations: int = 3

    # Project directories
    project_directory: str = "projects"
    state_directory: str = "data/state"
    checkpoint_directory: str = "data/checkpoints"
    event_directory: str = "data/events"
    memory_directory: str = "data/memory"
    log_directory: str = "logs"


settings = Settings()