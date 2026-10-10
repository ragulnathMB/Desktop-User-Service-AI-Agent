from __future__ import annotations

from ..errors import LLMError
from .base import LLMClient, post_json


class GeminiClient(LLMClient):
    provider = "gemini"

    def complete(self, system, messages, json_mode=False, max_tokens=1500):
        contents = []
        for m in messages:
            parts = [{"inline_data": {"mime_type": m.mime, "data": b}} for b in m.b64_images()]
            parts.append({"text": m.text or "(empty)"})
            contents.append({"role": "user" if m.role == "user" else "model", "parts": parts})
        gen = {"maxOutputTokens": max(max_tokens, 4096)}  # 2.5 models spend tokens on "thinking"
        if json_mode:
            gen["responseMimeType"] = "application/json"
        payload = {"contents": contents, "generationConfig": gen,
                   "systemInstruction": {"parts": [{"text": system}]}}
        headers = {"x-goog-api-key": self.api_key, "content-type": "application/json"}
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        data = post_json(url, headers, payload, self.timeout)
        cands = data.get("candidates") or []
        if not cands:
            raise LLMError(f"Gemini returned no candidates ({data.get('promptFeedback', 'blocked?')}).")
        parts = (cands[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            raise LLMError(f"Gemini returned an empty reply (finishReason={cands[0].get('finishReason')}).")
        return text
