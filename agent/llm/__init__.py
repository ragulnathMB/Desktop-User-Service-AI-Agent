from __future__ import annotations

from ..errors import LLMError
from .base import LLMClient, Message, extract_json
from .claude import ClaudeClient
from .gemini import GeminiClient
from .openai_client import OpenAIClient

PROVIDERS = {"claude": ClaudeClient, "gemini": GeminiClient, "openai": OpenAIClient}
PROVIDER_LABELS = {"claude": "Claude (Anthropic)", "gemini": "Gemini (Google)", "openai": "OpenAI"}


def create_client(cfg, provider: str | None = None) -> LLMClient:
    p = provider or cfg.data["provider"]
    if p not in PROVIDERS:
        raise LLMError(f"Unknown provider '{p}'")
    sec = cfg.data["providers"][p]
    return PROVIDERS[p](cfg.api_key(p), sec["model"], sec["base_url"])


__all__ = ["create_client", "LLMClient", "Message", "extract_json", "PROVIDERS", "PROVIDER_LABELS"]
