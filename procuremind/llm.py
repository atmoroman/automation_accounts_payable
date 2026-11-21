"""Thin wrapper around an OpenAI-compatible chat API (Groq or Gemini).

Keeping the LLM behind a small interface makes the rest of the code testable:
tests pass a fake client instead of calling a real API.
"""
from __future__ import annotations

import time
from typing import Protocol

from openai import APIStatusError, OpenAI, RateLimitError

from .config import Settings, get_settings


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str) -> str:
        """Return the model's reply as a JSON string."""
        ...


class OpenAICompatibleClient:
    def __init__(self, settings: Settings | None = None, max_retries: int = 4):
        self.settings = settings or get_settings()
        self.model = self.settings.model
        self.max_retries = max_retries
        self._client = OpenAI(api_key=self.settings.api_key, base_url=self.settings.base_url)

    def complete_json(self, system: str, user: str) -> str:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    temperature=self.settings.temperature,
                    response_format={"type": "json_object"},  # JSON mode
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return resp.choices[0].message.content or ""
            except RateLimitError:
                # Free tiers have per-minute limits -> exponential backoff
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
            except APIStatusError as e:
                if e.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        raise RuntimeError("unreachable")
