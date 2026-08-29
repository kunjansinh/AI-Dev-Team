import requests


class OllamaClient:
    """Client used to communicate with the local Ollama server."""

    def __init__(
        self,
        model: str = "qwen3:1.7b",
        timeout: int = 600,
    ) -> None:
        self.base_url = "http://localhost:11434"
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Send a prompt to Ollama and return the generated response."""

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": think,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return data["response"]