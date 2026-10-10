from __future__ import annotations

from ..errors import LLMError
from .base import LLMClient, Message, post_json


class ClaudeClient(LLMClient):
    provider = "claude"

    def complete(self, system, messages, json_mode=False, max_tokens=1500):
        msgs = []
        for m in messages:
            content = [{"type": "image", "source": {"type": "base64", "media_type": m.mime, "data": b}}
                       for b in m.b64_images()]
            content.append({"type": "text", "text": m.text or "(empty)"})
            msgs.append({"role": m.role, "content": content})
        payload = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": msgs}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        data = post_json(f"{self.base_url}/v1/messages", headers, payload, self.timeout)
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        if not text.strip():
            raise LLMError(f"Claude returned an empty reply (stop_reason={data.get('stop_reason')}).")
        return text
