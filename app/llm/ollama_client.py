from __future__ import annotations

import json
import os
from typing import Any

import requests


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.timeout = timeout

    def healthcheck(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/tags"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def generate_json(self, prompt: str) -> dict[str, Any]:
        """
        Ask Ollama for a strict JSON response.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0
            }
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        raw_text = data.get("response", "").strip()
        if not raw_text:
            raise ValueError("Ollama returned an empty response")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse Ollama JSON: {raw_text}") from exc
