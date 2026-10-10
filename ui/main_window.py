from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QStackedWidget

from agent.llm import PROVIDER_LABELS

from .glass import GlassWindow
from .icons import make_icon
from .pages import AgentPage, SummarizerPage
from .widgets import ModeSwitch


class MainWindow(GlassWindow):
    def __init__(self, ctl):
        super().__init__(ctl.registry, ctl.cfg, "Desktop AI Agent", size=(470, 680), min_size=(400, 520))
        self.ctl = ctl
        self.titlebar.add_button("", "Settings", ctl.open_settings).setIcon(make_icon("mdi6.cog"))
        self.titlebar.add_button("", "Show / hide live status window", ctl.toggle_status).setIcon(
            make_icon("mdi6.view-dashboard"))

        self.switch = ModeSwitch(["Auto summarizer", "Service agent"])
        self.switch.buttons[0].setIcon(make_icon("mdi6.camera"))
        self.switch.buttons[1].setIcon(make_icon("mdi6.robot"))
        self.body_layout.addWidget(self.switch)
        self.stack = QStackedWidget()
        self.sum_page = SummarizerPage(ctl)
        self.agent_page = AgentPage(ctl)
        self.stack.addWidget(self.sum_page)
        self.stack.addWidget(self.agent_page)
        self.body_layout.addWidget(self.stack, 1)
        self.footer = QLabel()
        self.footer.setObjectName("muted")
        self.footer.setAlignment(Qt.AlignCenter)
        self.body_layout.addWidget(self.footer)

        self.switch.changed.connect(self._on_mode)
        self.set_mode(int(ctl.cfg.data["ui"]["mode"]))
        self.refresh_footer()
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 24, scr.top() + 40)

    def set_mode(self, i: int):
        self.switch.set_index(i)
        self.stack.setCurrentIndex(i)

    def _on_mode(self, i: int):
        self.stack.setCurrentIndex(i)
        self.ctl.cfg.data["ui"]["mode"] = i
        self.ctl.cfg.save()

    def refresh_footer(self):
        p = self.ctl.cfg.data["provider"]
        m = self.ctl.cfg.data["providers"][p]["model"]
        self.footer.setText(f"{PROVIDER_LABELS[p]} · {m}")
