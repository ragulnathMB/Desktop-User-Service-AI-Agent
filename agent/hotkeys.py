"""Global hotkeys via pynput."""
from __future__ import annotations


class HotkeyManager:
    def __init__(self):
        self.listener = None

    def start(self, mapping: dict) -> None:
        """mapping: {'<ctrl>+<alt>+s': callable}. Raises on invalid combos / missing permissions."""
        self.stop()
        from pynput import keyboard
        self.listener = keyboard.GlobalHotKeys(mapping)
        self.listener.daemon = True
        self.listener.start()

    def stop(self) -> None:
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    @staticmethod
    def validate(combo: str) -> bool:
        try:
            from pynput import keyboard
        except Exception:
            return bool(combo)  # pynput unavailable here; can't validate
        try:
            keyboard.HotKey.parse(combo)
            return True
        except Exception:
            return False
