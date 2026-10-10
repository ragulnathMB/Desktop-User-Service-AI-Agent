"""The two mode pages: Auto Summarizer and Service Agent."""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
                               QTextBrowser, QVBoxLayout, QWidget)

from .icons import make_icon
from .theme import MD_CSS
from .widgets import ChatView, button, repolish


class SummarizerPage(QWidget):
    _done = Signal(str, bool)   # text, skipped
    _failed = Signal(str)

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        sc = ctl.cfg.data["summarizer"]
        self.busy = False
        self.entries: list[str] = []
        self.remaining = int(sc["interval_seconds"])

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        card = QWidget()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(9)

        r1 = QHBoxLayout()
        self.now_btn = button("Summarize now", "primary", "Hotkey: " + ctl.cfg.data["hotkeys"]["summarize"])
        self.now_btn.setIcon(make_icon("mdi6.camera", "#0B1020"))
        self.now_btn.clicked.connect(lambda: self.trigger(True))
        r1.addWidget(self.now_btn, 1)
        cl.addLayout(r1)

        r2 = QHBoxLayout()
        self.auto = QCheckBox("Auto every")
        self.auto.setChecked(sc["auto_enabled"])
        self.interval = QSpinBox()
        self.interval.setRange(5, 3600)
        self.interval.setSuffix(" s")
        self.interval.setValue(int(sc["interval_seconds"]))
        r2.addWidget(self.auto)
        r2.addWidget(self.interval)
        r2.addStretch(1)
        self.detail = QComboBox()
        for label, key in (("Brief", "brief"), ("Balanced", "balanced"), ("Detailed", "detailed")):
            self.detail.addItem(label, key)
        self.detail.setCurrentIndex(max(0, self.detail.findData(sc["detail"])))
        r2.addWidget(self.detail)
        cl.addLayout(r2)

        self.skip = QCheckBox("Skip when the screen hasn't changed")
        self.skip.setChecked(sc["skip_unchanged"])
        cl.addWidget(self.skip)
        self.focus = QLineEdit(sc["focus"])
        self.focus.setPlaceholderText("Focus (optional): e.g. “list action items”, “explain the error”")
        cl.addWidget(self.focus)
        lay.addWidget(card)

        self.view = QTextBrowser()
        self.view.document().setDefaultStyleSheet(MD_CSS)
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)
        self._render()

        foot = QHBoxLayout()
        self.countdown = QLabel("")
        self.countdown.setObjectName("muted")
        copy = button("Copy")
        copy.clicked.connect(self._copy)
        clear = button("Clear")
        clear.clicked.connect(self._clear)
        foot.addWidget(self.countdown, 1)
        foot.addWidget(copy)
        foot.addWidget(clear)
        lay.addLayout(foot)

        self._done.connect(self._on_done, Qt.QueuedConnection)
        self._failed.connect(self._on_failed, Qt.QueuedConnection)
        for w in (self.auto, self.skip):
            w.toggled.connect(self._persist)
        self.interval.valueChanged.connect(self._persist)
        self.detail.currentIndexChanged.connect(self._persist)
        self.focus.editingFinished.connect(self._persist)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self._tick(first=True)

    # ---- settings
    def _persist(self, *_):
        sc = self.ctl.cfg.data["summarizer"]
        sc.update(auto_enabled=self.auto.isChecked(), interval_seconds=self.interval.value(),
                  skip_unchanged=self.skip.isChecked(), detail=self.detail.currentData(),
                  focus=self.focus.text())
        self.ctl.cfg.save()
        self.remaining = self.interval.value()

    # ---- scheduling
    def _tick(self, first=False):
        if not self.auto.isChecked():
            self.countdown.setText("Auto mode off – use the button or the hotkey")
            return
        if self.busy:
            self.countdown.setText("Working…")
            return
        if not first:
            self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = self.interval.value()
            self.trigger(False)
        else:
            self.countdown.setText(f"Next automatic summary in {self.remaining}s")

    def trigger(self, force: bool):
        if self.busy:
            return
        self.busy = True
        self.now_btn.setEnabled(False)
        args = (self.focus.text(), self.detail.currentData(), self.skip.isChecked() and not force)
        threading.Thread(target=self._job, args=args, daemon=True).start()

    def _job(self, focus, detail, skip):
        try:
            text = self.ctl.summarizer.run(focus, detail, skip)
            self._done.emit(text or "", text is None)
        except Exception as e:
            self.ctl.bridge.log("error", str(e))
            self.ctl.bridge.set_state("error", str(e))
            self._failed.emit(str(e))

    def _on_done(self, text: str, skipped: bool):
        self.busy = False
        self.now_btn.setEnabled(True)
        self.remaining = self.interval.value()
        if not skipped and text:
            self.entries.insert(0, f"##### {time.strftime('%H:%M:%S')}\n\n{text}")
            del self.entries[40:]
            self._render()

    def _on_failed(self, msg: str):
        self.busy = False
        self.now_btn.setEnabled(True)
        self.remaining = self.interval.value()
        self.entries.insert(0, f"##### {time.strftime('%H:%M:%S')}\n\n**Could not summarize:** {msg}")
        self._render()

    def _render(self):
        if not self.entries:
            self.view.setMarkdown("**Nothing summarized yet.**\n\nPress *Summarize now*, switch on *Auto every*, "
                                  f"or use the hotkey `{self.ctl.cfg.data['hotkeys']['summarize']}`.")
        else:
            self.view.setMarkdown("\n\n---\n\n".join(self.entries))
        self.view.verticalScrollBar().setValue(0)

    def _copy(self):
        QApplication.clipboard().setText(self.view.toPlainText())

    def _clear(self):
        self.entries.clear()
        self._render()


class AgentPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.chat = ChatView()
        lay.addWidget(self.chat, 1)
        self.chat.add("assistant", "Hi! Tell me what to do on this computer — type it or use the microphone.\n\n"
                                   "For example: “Send a leave email to ramesh@gmail.com”. I'll look at the screen, "
                                   "act step by step, and check each step before moving on.")

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…")
        self.input.returnPressed.connect(self.send)
        self.mic = button("", tip="Speak a command (" + ctl.cfg.data["hotkeys"]["voice"] + ")")
        self.mic.setIcon(make_icon("mdi6.microphone"))
        self.mic.clicked.connect(ctl.toggle_voice)
        self.send_btn = button("Send", "primary")
        self.send_btn.clicked.connect(self.send)
        self.stop_btn = button("Stop", "danger", "Stop the task")
        self.stop_btn.setIcon(make_icon("mdi6.stop"))
        self.stop_btn.clicked.connect(ctl.stop_task)
        self.stop_btn.hide()
        row.addWidget(self.input, 1)
        row.addWidget(self.mic)
        row.addWidget(self.send_btn)
        row.addWidget(self.stop_btn)
        lay.addLayout(row)

        br = ctl.bridge
        br.sig_chat.connect(self.chat.add, Qt.QueuedConnection)
        br.sig_voice_state.connect(self.on_voice_state, Qt.QueuedConnection)
        br.sig_transcript.connect(self.on_transcript, Qt.QueuedConnection)
        br.sig_voice_error.connect(lambda m: self.chat.add("system", m), Qt.QueuedConnection)

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.chat.add("user", text)
        self.ctl.handle_user_text(text)

    def set_running(self, running: bool):
        self.stop_btn.setVisible(running)
        self.input.setPlaceholderText("Add a note for the assistant…" if running else "Type a command…")

    def on_voice_state(self, state: str):
        icons = {"listening": "mdi6.microphone-message", "transcribing": "mdi6.progress-clock",
                 "idle": "mdi6.microphone"}
        self.mic.setIcon(make_icon(icons.get(state, "mdi6.microphone"),
                                   "#F87171" if state == "listening" else "#EEF2FF"))
        self.mic.setProperty("variant", "rec" if state == "listening" else None)
        repolish(self.mic)

    def on_transcript(self, text: str):
        self.input.setText(text)
        if self.ctl.cfg.data["voice"]["auto_send"]:
            self.send()
