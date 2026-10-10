from __future__ import annotations

from ..errors import LLMError
from .base import LLMClient, post_json


class OpenAIClient(LLMClient):
    provider = "openai"

    def complete(self, system, messages, json_mode=False, max_tokens=1500):
        msgs = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "assistant" or not m.images:
                msgs.append({"role": m.role, "content": m.text or "(empty)"})
                continue
            content = [{"type": "text", "text": m.text or "(empty)"}]
            for b in m.b64_images():
                content.append({"type": "image_url",
                                "image_url": {"url": f"data:{m.mime};base64,{b}", "detail": "high"}})
            msgs.append({"role": "user", "content": content})
        payload = {"model": self.model, "messages": msgs, "max_completion_tokens": max(max_tokens, 2048)}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}
        data = post_json(f"{self.base_url}/chat/completions", headers, payload, self.timeout)
        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") if choices else "") or ""
        if not text.strip():
            raise LLMError("OpenAI returned an empty reply.")
        return text
