"""Auto screen summarizer: screenshot -> online LLM -> summary text."""
from __future__ import annotations

from .llm import Message
from .prompts import summarizer_system, summarizer_user


class Summarizer:
    def __init__(self, cfg, capture, make_client, events):
        self.cfg, self.capture, self.make_client, self.ev = cfg, capture, make_client, events
        self.last_shot = None
        self.last_summary = ""

    def run(self, focus: str = "", detail: str = "balanced", skip_unchanged: bool = False):
        """Returns summary markdown, or None when skipped because the screen did not change."""
        ev = self.ev
        ev.set_state("capturing", "Taking screenshot")
        shot = self.capture.grab(grid=False)
        ev.log("capture", f"Screenshot taken ({shot.width}×{shot.height}) – assistant windows hidden")
        if skip_unchanged and self.last_shot is not None and shot.diff(self.last_shot) < 0.01:
            ev.log("info", "Screen unchanged – skipped (saves API calls)")
            ev.set_state("idle", "Screen unchanged")
            return None
        self.last_shot = shot
        client = self.make_client()
        ev.set_state("thinking", f"Sending screenshot to {client.provider} ({client.model})")
        ev.log("llm", f"Asking {client.provider} / {client.model} to summarize…")
        text = client.complete(summarizer_system(self.cfg.data["language"], detail),
                               [Message("user", summarizer_user(focus, self.last_summary), [shot.jpeg])],
                               max_tokens=1500)
        self.last_summary = text
        ev.log("ok", "Summary received")
        ev.set_state("idle", "Ready")
        return text
