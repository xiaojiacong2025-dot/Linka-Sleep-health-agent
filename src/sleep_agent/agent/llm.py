from __future__ import annotations

import time
from typing import Any

import httpx

from sleep_agent.settings import Settings


class LLMConfigurationError(RuntimeError):
    pass


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings):
        if not settings.llm_configured:
            raise LLMConfigurationError("LLM_API_KEY and LLM_MODEL are required")
        self.settings = settings

    def chat(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict:
        cfg = self.settings.config["agent"]
        payload: dict[str, Any] = {
            "model": self.settings.llm_model, "messages": messages, "temperature": 0.1,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        last_error: Exception | None = None
        for attempt in range(cfg["llm_retries"] + 1):
            try:
                with httpx.Client(timeout=cfg["llm_timeout_seconds"]) as client:
                    response = client.post(
                        f"{self.settings.llm_base_url}/chat/completions",
                        json=payload, headers=headers,
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]
            except (httpx.HTTPError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt < cfg["llm_retries"]:
                    time.sleep(0.5)
        raise RuntimeError(f"LLM request failed: {type(last_error).__name__}")

