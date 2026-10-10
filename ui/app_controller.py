"""Wires everything together: windows, tray, hotkeys, agent + summarizer threads."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from agent.errors import Cancelled
from agent.hotkeys import HotkeyManager
from agent.llm import create_client
from agent.screen import ScreenCapture
from agent.service import ServiceAgent
from agent.summarizer import Summarizer
from agent.voice import VoiceService

from .bridge import Bridge
from .icons import make_app_icon
from .main_window import MainWindow
from .settings_window import SettingsWindow
from .status_window import StatusWindow
from .window_manager import WindowRegistry


class AppController(QObject):
    sig_hotkey = Signal(str)

    def __init__(self, app, cfg):
        super().__init__()
        self.app, self.cfg = app, cfg
        self.registry = WindowRegistry(cfg)
        self.bridge = Bridge()
        self.capture = ScreenCapture(cfg, self.registry)
        self.summarizer = Summarizer(cfg, self.capture, self.make_llm, self.bridge)
        self.desktop = None            # DesktopController, created lazily (after Qt DPI setup)
        self.cancel = threading.Event()
        self.task_running = False
        self.hotkeys = HotkeyManager()
        self.voice = VoiceService(cfg,
                                  lambda s: self.bridge.sig_voice_state.emit(s),
                                  lambda t: self.bridge.sig_transcript.emit(t),
                                  self._voice_error)
        self.settings_win = None

        self.main = MainWindow(self)
        self.status = StatusWindow(self)
        self.sig_hotkey.connect(self._on_hotkey, Qt.QueuedConnection)
        self.bridge.sig_ask.connect(self._on_ask, Qt.QueuedConnection)
        self.bridge.sig_task_finished.connect(self._on_finished, Qt.QueuedConnection)
        self._setup_tray()
        self.apply_hotkeys()

    # ------------------------------------------------------------ helpers
    def make_llm(self):
        return create_client(self.cfg)

    def show_initial(self):
        if not self.cfg.data["ui"]["start_hidden"]:
            self.main.show_front()
        if not self.cfg.api_key(self.cfg.data["provider"]):
            self.main.show_front()
            self.open_settings()

    # --------------------------------------------------------------- tray
    def _setup_tray(self):
        self.tray = None
        if not self.cfg.data["ui"]["show_tray"] or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(), self.app)
        self.tray.setToolTip("Desktop AI Agent")
        m = QMenu()
        for text, fn in (("Show / hide window", self.toggle_main), ("Show / hide live status", self.toggle_status),
                         ("Summarize screen now", lambda: self._on_hotkey("summarize")),
                         ("Stop running task", self.stop_task), ("Settings…", self.open_settings),
                         ("Quit", self.quit)):
            a = QAction(text, m)
            a.triggered.connect(fn)
            m.addAction(a)
        self._tray_menu = m
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.toggle_main() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def toggle_main(self):
        self.main.hide() if self.main.isVisible() else self.main.show_front()

    def toggle_status(self):
        self.status.hide() if self.status.isVisible() else self.status.show()

    def quit(self):
        self.cancel.set()
        self.hotkeys.stop()
        self.app.quit()

    # ------------------------------------------------------------ hotkeys
    def apply_hotkeys(self):
        hk = self.cfg.data["hotkeys"]
        mapping = {hk[name]: (lambda n=name: self.sig_hotkey.emit(n)) for name in hk if hk[name]}
        try:
            self.hotkeys.start(mapping)
        except Exception as e:
            self.bridge.log("warn", f"Global hotkeys unavailable: {e}")

    def _on_hotkey(self, name: str):
        if name == "summarize":
            self.main.show_front()
            self.main.set_mode(0)
            self.main.sum_page.trigger(True)
        elif name == "toggle_window":
            self.toggle_main()
        elif name == "stop_agent":
            self.stop_task()
        elif name == "voice":
            self.main.show_front()
            self.main.set_mode(1)
            self.main.agent_page.input.setFocus()
            self.toggle_voice()

    # -------------------------------------------------------------- voice
    def toggle_voice(self):
        if self.voice.active:
            self.voice.stop()
        else:
            self.voice.start()

    def _voice_error(self, msg: str):
        self.bridge.sig_voice_error.emit(msg)
        self.bridge.log("warn", msg)

    # ------------------------------------------------------------- agent
    def handle_user_text(self, text: str):
        b = self.bridge
        if b.awaiting_answer:
            b.provide_answer(text)
            if self.cfg.data["agent"]["minimize_on_task"]:
                self.main.hide()
        elif self.task_running:
            b.push_inbox(text)
            self.main.agent_page.chat.add("system", "Noted – I'll take that into account on the next step.")
        else:
            self.run_task(text)

    def run_task(self, text: str):
        if self.task_running:
            return
        self.task_running = True
        self.cancel.clear()
        self.main.agent_page.set_running(True)
        self.status.show()
        if self.cfg.data["agent"]["minimize_on_task"]:
            self.main.hide()
        self.bridge.set_state("thinking", "Starting task…")
        threading.Thread(target=self._task_main, args=(text,), daemon=True).start()

    def _task_main(self, text: str):
        br = self.bridge
        try:
            client = self.make_llm()
            if self.desktop is None:
                from agent.controller import DesktopController  # lazy import (see DesktopController)
                self.desktop = DesktopController(self.cfg)
            ServiceAgent(self.cfg, client, self.capture, self.desktop, br).run(text, self.cancel)
        except Cancelled as e:
            br.log("warn", "Task stopped" + (f": {e}" if str(e) else ""))
            br.finish(False, "Stopped.")
        except Exception as e:
            br.log("error", f"{type(e).__name__}: {e}")
            br.finish(False, f"Problem: {e}")

    def stop_task(self):
        if self.task_running:
            self.cancel.set()
            self.bridge.log("warn", "Stopping…")

    def _on_ask(self, question: str):
        self.main.agent_page.chat.add("assistant", question)
        self.main.set_mode(1)
        self.main.show_front()
        self.main.agent_page.input.setFocus()

    def _on_finished(self, ok: bool, message: str):
        self.task_running = False
        self.main.agent_page.set_running(False)
        prefix = "Completed: " if ok else "Warning: "
        self.main.agent_page.chat.add("assistant", prefix + message)
        self.bridge.set_state("done" if ok else "error", message)
        if self.cfg.data["agent"]["minimize_on_task"]:
            self.main.show_front()

    # ----------------------------------------------------------- settings
    def open_settings(self):
        if self.settings_win is not None:
            self.settings_win.close()
            self.settings_win.deleteLater()
        self.settings_win = SettingsWindow(self)
        self.settings_win.saved.connect(self.apply_settings)
        self.settings_win.show_front()

    def apply_settings(self):
        self.apply_hotkeys()
        self.main.refresh_footer()
        for w in (self.main, self.status):
            w.update()
        if self.tray:
            self.tray.setVisible(self.cfg.data["ui"]["show_tray"])
