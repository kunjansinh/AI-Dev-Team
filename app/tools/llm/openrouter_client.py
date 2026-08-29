from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()


class OpenRouterClient:
    """Client used to communicate with OpenRouter's API."""

    def __init__(
        self,
        model: str = "openrouter/free",
        timeout: int = 120,
    ) -> None:
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model
        self.timeout = timeout

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not configured."
            )

        self.api_key = api_key

    def generate(
        self,
        prompt: str,
        think: bool = False,
    ) -> str:
        """Send a prompt to OpenRouter and return the generated response."""

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]