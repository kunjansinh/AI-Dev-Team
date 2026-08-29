from app.tools.llm.ollama_client import OllamaClient


def main():
    client = OllamaClient()

    response = client.generate(
        "You are a software development manager. "
        "In one paragraph, explain what your role should be "
        "in an AI development team."
    )

    print("\nManager response:\n")
    print(response)


if __name__ == "__main__":
    main()