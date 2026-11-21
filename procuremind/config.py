"""Central configuration. All settings come from environment variables (.env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Both providers expose an OpenAI-compatible API, so one client works for both.
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "openai/gpt-oss-120b",
        "key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
        "key_env": "GEMINI_API_KEY",
    },
}


@dataclass(frozen=True)
class Settings:
    provider: str
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0  # deterministic output for data extraction


def get_settings() -> Settings:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER must be one of {list(PROVIDERS)}, got '{provider}'")
    p = PROVIDERS[provider]
    api_key = os.getenv(p["key_env"], "")
    if not api_key:
        raise RuntimeError(
            f"Missing {p['key_env']}. Copy .env.example to .env and paste your key there."
        )
    return Settings(
        provider=provider,
        base_url=p["base_url"],
        model=os.getenv("LLM_MODEL") or p["default_model"],
        api_key=api_key,
    )
