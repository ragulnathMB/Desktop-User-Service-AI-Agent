"""Live status window: shows what the app and the LLM are doing, and any problem."""
from __future__ import annotations

import html
import time

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTextBrowser, QWidget

from .glass import GlassWindow
from .icons import make_icon
from .theme import LEVELS, STATE_COLORS, STATE_LABELS
from .widgets import button, repolish


class StatusWindow(GlassWindow):
    def __init__(self, ctl):
        super().__init__(ctl.registry, ctl.cfg, "Live status", size=(380, 460), min_size=(320, 300))
        self.ctl = ctl
        br = ctl.bridge

        head = QHBoxLayout()
        self.pill = QLabel("Idle")
        self.pill.setObjectName("pill")
        self.step = QLabel("")
        self.step.setObjectName("muted")
        head.addWidget(self.pill)
        head.addStretch(1)
        head.addWidget(self.step)
        self.body_layout.addLayout(head)
        self.detail = QLabel("Ready when you are.")
        self.detail.setWordWrap(True)
        self.body_layout.addWidget(self.detail)

        self.log = QTextBrowser()
        self.log.document().setMaximumBlockCount(600)
        self._log_icons = set()
        self.body_layout.addWidget(self.log, 1)

        # approval row (shown only when the agent asks permission)
        self.confirm_box = QWidget()
        cl = QHBoxLayout(self.confirm_box)
        cl.setContentsMargins(0, 0, 0, 0)
        self.confirm_lbl = QLabel("")
        self.confirm_lbl.setWordWrap(True)
        self.allow = button("Allow", "primary")
        self.deny = button("Deny", "danger")
        cl.addWidget(self.confirm_lbl, 1)
        cl.addWidget(self.allow)
        cl.addWidget(self.deny)
        self.confirm_box.hide()
        self.body_layout.addWidget(self.confirm_box)
        self.allow.clicked.connect(lambda: self._answer(True))
        self.deny.clicked.connect(lambda: self._answer(False))

        row = QHBoxLayout()
        self.stop_btn = button("Stop", "danger", "Stop the running task (Ctrl+Alt+X)")
        self.stop_btn.setIcon(make_icon("mdi6.stop"))
        self.stop_btn.clicked.connect(ctl.stop_task)
        clear = button("Clear log")
        clear.clicked.connect(self.log.clear)
        row.addWidget(self.stop_btn)
        row.addStretch(1)
        row.addWidget(clear)
        row.addSpacing(18)
        self.body_layout.addLayout(row)

        br.sig_state.connect(self.on_state, Qt.QueuedConnection)
        br.sig_log.connect(self.on_log, Qt.QueuedConnection)
        br.sig_step.connect(self.on_step, Qt.QueuedConnection)
        br.sig_confirm.connect(self.on_confirm, Qt.QueuedConnection)
        self.on_state("idle", "Ready when you are.")
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 24, scr.bottom() - self.height() - 24)

    def on_state(self, state: str, detail: str):
        col = STATE_COLORS.get(state, "#94A3B8")
        self.pill.setText(STATE_LABELS.get(state, state))
        r, g, b = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
        self.pill.setStyleSheet(f"QLabel#pill {{ background: rgba({r},{g},{b},50); color: {col}; "
                                f"border: 1px solid rgba({r},{g},{b},140); }}")
        repolish(self.pill)
        self.detail.setText(detail)
        if state in ("idle", "done", "error"):
            self.step.setText("")

    def on_step(self, i: int, n: int):
        self.step.setText(f"Step {i} / {n}")

    def on_log(self, level: str, text: str):
        icon_name, col = LEVELS.get(level, LEVELS["info"])
        icon_source = f"status-icon:{icon_name}"
        if icon_source not in self._log_icons:
            pixmap = make_icon(icon_name, col).pixmap(14, 14)
            self.log.document().addResource(QTextDocument.ImageResource, QUrl(icon_source), pixmap)
            self._log_icons.add(icon_source)
        ts = time.strftime("%H:%M:%S")
        self.log.append(f'<span style="color:#7C86AD">{ts}</span> '
                        f'<img src="{icon_source}" width="14" height="14"> '
                        f'<span style="color:{col}">{html.escape(text)}</span>')
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_confirm(self, question: str):
        self.confirm_lbl.setText(question)
        self.confirm_box.show()
        self.show_front()

    def _answer(self, ok: bool):
        self.confirm_box.hide()
        self.ctl.bridge.provide_confirm(ok)
        self.on_log("user", "You allowed the action" if ok else "You denied the action")
