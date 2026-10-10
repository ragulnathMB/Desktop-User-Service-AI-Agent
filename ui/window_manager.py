"""Applies stealth (no taskbar button, hidden from screenshots, blur) to every window."""
from __future__ import annotations

from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, Slot
from PySide6.QtWidgets import QApplication

from agent import platform_utils as pu


class WindowRegistry(QObject):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.windows: list = []
        self.all_excluded = True   # every window natively invisible to capture?
        self._hidden: list = []

    # -- called once per window after its native handle exists
    def apply(self, w) -> None:
        hwnd = int(w.winId())
        if pu.IS_WIN:
            pu.hide_from_taskbar(hwnd)
            self.all_excluded = pu.exclude_from_capture(hwnd) and self.all_excluded
            if self.cfg.data["ui"]["native_blur"] and pu.enable_blur(hwnd):
                w.set_blur_active(True)
        else:
            if pu.IS_MAC:
                pu.mac_prepare_window(hwnd)
            self.all_excluded = False  # not reliable -> fall back to hiding during capture
        if w not in self.windows:
            self.windows.append(w)

    # -- capture hook (ScreenCapture calls these from a worker thread)
    def needs_hide(self) -> bool:
        mode = self.cfg.data["capture"]["hide_mode"]
        if mode == "always":
            return True
        if mode == "never":
            return False
        return not self.all_excluded

    def hide(self) -> None:
        self._invoke("_do_hide")

    def restore(self) -> None:
        self._invoke("_do_restore")

    def _invoke(self, name: str) -> None:
        if QThread.currentThread() == self.thread():
            getattr(self, name)()
        else:
            QMetaObject.invokeMethod(self, name, Qt.BlockingQueuedConnection)

    @Slot()
    def _do_hide(self):
        self._hidden = [w for w in self.windows if w.isVisible()]
        for w in self._hidden:
            w.setWindowOpacity(0.0)
        QApplication.processEvents()

    @Slot()
    def _do_restore(self):
        for w in self._hidden:
            w.setWindowOpacity(1.0)
        self._hidden = []
