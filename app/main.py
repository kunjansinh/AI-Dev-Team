from app.config.settings import settings
from app.tools.llm.model_registry import ModelRegistry


def main() -> None:
    registry = ModelRegistry()

    print("=" * 60)
    print("AI DEV TEAM")
    print("=" * 60)

    print(f"Manager model : {settings.manager_model}")
    print(f"Default model : {settings.default_model}")
    print(f"Heavy model   : {settings.heavy_model}")

    print("\nRegistered models:")

    for model_name in registry.list_models():
        model = registry.get(model_name)

        print(
            f"- {model.name}: "
            f"{model.purpose}"
        )

    print("\nAI Dev Team environment is ready.")


if __name__ == "__main__":
    main()