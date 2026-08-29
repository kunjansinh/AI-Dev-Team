from fastapi import FastAPI

from app.config.settings import settings
from app.tools.llm.model_registry import ModelRegistry


app = FastAPI(title="AI Dev Team")


@app.get("/")
def root():
    return {
        "status": "online",
        "message": "AI Dev Team is running"
    }


@app.get("/healthz")
def healthz():
    return {
        "status": "healthy"
    }


@app.get("/models")
def models():
    registry = ModelRegistry()

    registered_models = []

    for model_name in registry.list_models():
        model = registry.get(model_name)

        registered_models.append({
            "name": model.name,
            "purpose": model.purpose
        })

    return {
        "manager_model": settings.manager_model,
        "default_model": settings.default_model,
        "heavy_model": settings.heavy_model,
        "models": registered_models
    }


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