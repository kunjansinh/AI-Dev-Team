# app/tools/llm/cloud_client.py
import os
import time
import requests

class CloudClientError(Exception):
    pass

class CloudClient:
    """
    OpenRouter client. Same call shape as OllamaClient so agents don't
    need to know which backend they're talking to.
    """
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None, requests_per_minute: int = 15):
        self.api_key = api_key or os.environ["OPENROUTER_API_KEY"]
        self._min_interval = 60.0 / requests_per_minute
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    def generate(self, prompt: str, model: str, timeout: int = 60, **kwargs) -> str:
        """Match this method name/signature to whatever OllamaClient.generate()
        currently uses in your codebase, so ModelRegistry can call either
        client interchangeably."""
        self._throttle()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise CloudClientError(f"OpenRouter call failed: {e}") from e

        data = resp.json()
        return data["choices"][0]["message"]["content"]