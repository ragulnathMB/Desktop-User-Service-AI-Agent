"""Settings storage (JSON in the user's config folder)."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

APP_NAME = "DesktopAIAgent"

DEFAULTS = {
    "provider": "claude",  # claude | gemini | openai
    "providers": {
        "claude": {"api_key": "", "model": "claude-sonnet-5-5", "base_url": "https://api.anthropic.com"},
        "gemini": {"api_key": "", "model": "gemini-2.5-flash", "base_url": "https://generativelanguage.googleapis.com"},
        "openai": {"api_key": "", "model": "gpt-4o", "base_url": "https://api.openai.com/v1"},
    },
    "language": "English",
    "summarizer": {
        "auto_enabled": False,
        "interval_seconds": 30,
        "skip_unchanged": True,
        "detail": "balanced",  # brief | balanced | detailed
        "focus": "",
    },
    "agent": {
        "max_steps": 40,
        "verify_each_step": True,
        "max_retries": 2,
        "post_action_delay": 1.0,
        "human_like": True,
        "mouse_speed": 1.0,
        "typing_mode": "auto",  # auto | type | paste
        "confirm_risky": True,
        "minimize_on_task": True,
        "grid_overlay": False,
    },
    "capture": {"max_dimension": 1280, "jpeg_quality": 80, "hide_mode": "auto"},  # auto | always | never
    "hotkeys": {
        "summarize": "<ctrl>+<alt>+s",
        "toggle_window": "<ctrl>+<alt>+<space>",
        "stop_agent": "<ctrl>+<alt>+x",
        "voice": "<ctrl>+<alt>+v",
    },
    "voice": {"engine": "google", "language": "en-US", "silence_seconds": 1.6, "max_seconds": 30, "auto_send": True},
    "ui": {"opacity": 0.82, "native_blur": True, "show_tray": True, "start_hidden": False, "mode": 0},
}

ENV_KEYS = {
    "claude": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
}


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict | None = None, path: Path | None = None):
        self.data = deep_merge(DEFAULTS, data or {})
        self.path = path

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or (config_dir() / "config.json")
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        return cls(data, path)

    def save(self) -> None:
        if not self.path:
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)

    def api_key(self, provider: str) -> str:
        key = (self.data["providers"][provider].get("api_key") or "").strip()
        if key:
            return key
        for env in ENV_KEYS.get(provider, []):
            if os.environ.get(env):
                return os.environ[env].strip()
        return ""

    def section(self, name: str) -> dict:
        return self.data[name]
