"""DesktopController: moves the mouse and presses keys like a human would."""
from __future__ import annotations

import math
import random
import time

from .errors import Cancelled, ControllerError
from .platform_utils import IS_MAC, IS_WIN

KEY_ALIASES = {
    "control": "ctrl", "ctl": "ctrl", "return": "enter", "escape": "esc", "windows": "win",
    "super": "win", "option": "alt", "del": "delete", "pgup": "pageup", "pgdn": "pagedown",
    "page_up": "pageup", "page_down": "pagedown", "spacebar": "space", "arrowup": "up",
    "arrowdown": "down", "arrowleft": "left", "arrowright": "right", "caps": "capslock",
    "ins": "insert", "plus": "+", "cmd": "command", "meta": "command",
}


def normalize_keys(spec: str) -> list[str]:
    """'Ctrl + L' -> ['ctrl','l'] (cmd/win mapped for the current OS)."""
    parts = [p.strip().lower() for p in spec.replace(" ", "").split("+") if p.strip()]
    if spec.strip().endswith("++"):
        parts.append("+")
    out = []
    for p in parts:
        p = KEY_ALIASES.get(p, p)
        if p in ("win", "command"):
            p = "command" if IS_MAC else "win"
        out.append(p)
    return out


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


class DesktopController:
    def __init__(self, cfg):
        # Imported lazily: pyautogui must load AFTER Qt has set its DPI awareness.
        import pyautogui
        self.pg = pyautogui
        self.cfg = cfg
        pyautogui.FAILSAFE = True  # slam the mouse into a screen corner to abort
        pyautogui.PAUSE = 0.03
        self.ac = cfg.data["agent"]

    # ------------------------------------------------------------ helpers
    def _screen(self):
        w, h = self.pg.size()
        return int(w), int(h)

    def map_point(self, x: float, y: float, shot) -> tuple[int, int]:
        sw, sh = self._screen()
        X = int(round(x * sw / shot.width))
        Y = int(round(y * sh / shot.height))
        return max(3, min(sw - 4, X)), max(3, min(sh - 4, Y))  # stay off the fail-safe corners

    def _sleep(self, s: float):
        time.sleep(s * (random.uniform(0.8, 1.25) if self.ac["human_like"] else 1.0))

    # -------------------------------------------------------------- mouse
    def move_to(self, X: int, Y: int):
        pg = self.pg
        speed = max(0.2, float(self.ac["mouse_speed"]))
        if not self.ac["human_like"]:
            pg.moveTo(X, Y, duration=0.15 / speed)
            return
        sx, sy = pg.position()
        dist = math.hypot(X - sx, Y - sy)
        if dist < 2:
            return
        duration = (0.22 + dist / 2200 + random.uniform(0.05, 0.2)) / speed
        steps = max(10, int(duration * 90))
        # quadratic bezier with a random bend => natural curved path
        bend = min(120, dist * 0.15)
        cx = (sx + X) / 2 + random.uniform(-bend, bend)
        cy = (sy + Y) / 2 + random.uniform(-bend, bend)
        for i in range(1, steps + 1):
            t = _ease(i / steps)
            px = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t ** 2 * X
            py = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t ** 2 * Y
            pg.moveTo(px, py, _pause=False)
            time.sleep(duration / steps)
        pg.moveTo(X, Y)
        time.sleep(random.uniform(0.04, 0.12))

    def click(self, X: int, Y: int, button="left", clicks=1):
        self.move_to(X, Y)
        self.pg.click(X, Y, clicks=clicks, interval=0.09, button=button)

    def drag(self, X1, Y1, X2, Y2):
        self.move_to(X1, Y1)
        self.pg.mouseDown()
        time.sleep(0.12)
        self.move_to(X2, Y2)
        time.sleep(0.1)
        self.pg.mouseUp()

    def scroll(self, notches: int, X=None, Y=None):
        if X is not None:
            self.move_to(X, Y)
        unit = 120 if IS_WIN else (3 if IS_MAC else 1)
        remaining = int(notches)
        while remaining != 0:  # in small bursts, like a human wheel
            n = max(-5, min(5, remaining))
            self.pg.scroll(n * unit)
            remaining -= n
            time.sleep(0.08)

    # ----------------------------------------------------------- keyboard
    def type_text(self, text: str, enter: bool = False):
        mode = self.ac["typing_mode"]
        ascii_only = all(ord(c) < 128 for c in text)
        if mode == "paste" or (mode == "auto" and not ascii_only):
            self._paste(text)
        else:
            for ch in text:
                self.pg.write(ch, interval=0)
                time.sleep(random.uniform(0.015, 0.075) if self.ac["human_like"] else 0.005)
        if enter:
            time.sleep(0.15)
            self.pg.press("enter")

    def _paste(self, text: str):
        import pyperclip
        try:
            old = pyperclip.paste()
        except Exception:
            old = None
        pyperclip.copy(text)
        time.sleep(0.08)
        self.pg.hotkey("command" if IS_MAC else "ctrl", "v")
        time.sleep(0.25)
        if old is not None:
            try:
                pyperclip.copy(old)
            except Exception:
                pass

    def press(self, spec: str):
        keys = normalize_keys(spec)
        if not keys:
            raise ControllerError(f"Empty key spec '{spec}'")
        bad = [k for k in keys if k not in self.pg.KEYBOARD_KEYS]
        if bad:
            raise ControllerError(f"Unknown key(s): {', '.join(bad)}")
        if len(keys) == 1:
            self.pg.press(keys[0])
        else:
            self.pg.hotkey(*keys, interval=0.06)

    # ------------------------------------------------------------ execute
    def execute(self, a: dict, shot, cancel=None) -> None:
        t = a["type"]
        try:
            if t in ("click", "double_click", "right_click"):
                X, Y = self.map_point(a["x"], a["y"], shot)
                self.click(X, Y, "right" if t == "right_click" else "left", 2 if t == "double_click" else 1)
            elif t == "move":
                self.move_to(*self.map_point(a["x"], a["y"], shot))
            elif t == "drag":
                X1, Y1 = self.map_point(a["x"], a["y"], shot)
                X2, Y2 = self.map_point(a["x2"], a["y2"], shot)
                self.drag(X1, Y1, X2, Y2)
            elif t == "type":
                self.type_text(a["text"], a.get("enter", False))
            elif t == "key":
                self.press(a["keys"])
            elif t == "scroll":
                if "x" in a:
                    X, Y = self.map_point(a["x"], a["y"], shot)
                    self.scroll(a["amount"], X, Y)
                else:
                    self.scroll(a["amount"])
            elif t == "wait":
                end = time.time() + a["seconds"]
                while time.time() < end:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    time.sleep(0.1)
            else:
                raise ControllerError(f"Cannot execute action '{t}'")
        except self.pg.FailSafeException:
            raise Cancelled("Fail-safe triggered (mouse moved to a screen corner)")
        except (ControllerError, Cancelled):
            raise
        except Exception as e:  # pyautogui / OS problems
            raise ControllerError(f"{type(e).__name__}: {e}")
