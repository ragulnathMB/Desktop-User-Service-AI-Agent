"""Common LLM client interface + HTTP helper with retries."""
from __future__ import annotations

import base64
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

from ..errors import LLMError


@dataclass
class Message:
    role: str  # "user" | "assistant"
    text: str
    images: list = field(default_factory=list)  # raw image bytes
    mime: str = "image/jpeg"

    def b64_images(self) -> list[str]:
        return [base64.b64encode(i).decode("ascii") for i in self.images]


RETRY_CODES = {408, 409, 429, 500, 502, 503, 504, 529}


def _error_text(r: requests.Response) -> str:
    try:
        j = r.json()
        if isinstance(j, dict):
            e = j.get("error", j)
            if isinstance(e, dict):
                return str(e.get("message") or e)
            return str(e)
    except Exception:
        pass
    return r.text[:300]


def post_json(url: str, headers: dict, payload: dict, timeout: int = 90, retries: int = 3) -> dict:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            last = LLMError(f"Network error: {e}")
        else:
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    raise LLMError("The API returned invalid JSON.")
            err = LLMError(f"HTTP {r.status_code}: {_error_text(r)}")
            if r.status_code not in RETRY_CODES:
                raise err
            last = err
        if attempt < retries:
            time.sleep(min(1.5 * 2 ** attempt, 10))
    raise last or LLMError("Unknown API failure")


class LLMClient(ABC):
    provider = "base"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: int = 90):
        if not api_key:
            raise LLMError(f"No API key for {self.provider}. Open Settings and add one.")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @abstractmethod
    def complete(self, system: str, messages: list[Message], json_mode: bool = False,
                 max_tokens: int = 1500) -> str:
        """Send messages (optionally with images) and return the text reply."""

    def ping(self) -> str:
        return self.complete("Reply with the single word OK.", [Message("user", "ping")], max_tokens=1024)


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of an LLM reply (tolerates fences/prose)."""
    text = (text or "").strip()
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                if isinstance(obj, dict):
                    return obj
            except ValueError:
                continue
    raise ValueError("no JSON object found in model reply")
