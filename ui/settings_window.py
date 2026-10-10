from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QScrollArea, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from agent.hotkeys import HotkeyManager
from agent.llm import PROVIDER_LABELS, PROVIDERS
from agent.llm.base import LLMError

from .glass import GlassWindow
from .widgets import button

MODEL_HINTS = {
    "claude": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5", "claude-sonnet-4-5"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "openai": ["gpt-4o", "gpt-4.1", "gpt-4o-mini", "gpt-5"],
}


def _form() -> tuple[QWidget, QFormLayout]:
    w = QWidget()
    f = QFormLayout(w)
    f.setContentsMargins(4, 8, 4, 8)
    f.setSpacing(10)
    f.setLabelAlignment(Qt.AlignLeft)
    f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    return w, f


def _scroll(w: QWidget) -> QScrollArea:
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setWidget(w)
    return s


class SettingsWindow(GlassWindow):
    saved = Signal()
    _test_result = Signal(str, bool)

    def __init__(self, ctl):
        super().__init__(ctl.registry, ctl.cfg, "Settings", size=(500, 600), min_size=(420, 480))
        self.ctl = ctl
        d = ctl.cfg.data
        self.tabs = QTabWidget()
        self.body_layout.addWidget(self.tabs, 1)

        # ---------------- AI provider
        w, f = _form()
        self.provider = QComboBox()
        for k, v in PROVIDER_LABELS.items():
            self.provider.addItem(v, k)
        self.provider.setCurrentIndex(self.provider.findData(d["provider"]))
        f.addRow("Active provider", self.provider)
        self.language = QLineEdit(d["language"])
        f.addRow("Reply language", self.language)
        self.pw = {}
        for key, label in PROVIDER_LABELS.items():
            sec = d["providers"][key]
            lbl = QLabel(label)
            lbl.setObjectName("section")
            f.addRow(lbl)
            api = QLineEdit(sec["api_key"])
            api.setEchoMode(QLineEdit.Password)
            api.setPlaceholderText("API key (or set the environment variable)")
            model = QComboBox()
            model.setEditable(True)
            model.addItems(MODEL_HINTS[key])
            model.setCurrentText(sec["model"])
            base = QLineEdit(sec["base_url"])
            test = button("Test connection")
            res = QLabel("")
            res.setObjectName("muted")
            res.setWordWrap(True)
            test.clicked.connect(lambda _=False, k=key: self._test(k))
            f.addRow("API key", api)
            f.addRow("Model", model)
            f.addRow("Base URL", base)
            row = QHBoxLayout()
            row.addWidget(test)
            row.addWidget(res, 1)
            f.addRow(row)
            self.pw[key] = (api, model, base, res)
        self.tabs.addTab(_scroll(w), "AI provider")
        self._test_result.connect(self._on_test, Qt.QueuedConnection)

        # ---------------- Agent
        a = d["agent"]
        w, f = _form()
        self.max_steps = QSpinBox(); self.max_steps.setRange(1, 300); self.max_steps.setValue(a["max_steps"])
        self.verify = QCheckBox("Verify every step with a new screenshot"); self.verify.setChecked(a["verify_each_step"])
        self.retries = QSpinBox(); self.retries.setRange(0, 6); self.retries.setValue(a["max_retries"])
        self.delay = QDoubleSpinBox(); self.delay.setRange(0.0, 15.0); self.delay.setSingleStep(0.5)
        self.delay.setValue(a["post_action_delay"]); self.delay.setSuffix(" s")
        self.human = QCheckBox("Human-like mouse & typing"); self.human.setChecked(a["human_like"])
        self.speed = QSlider(Qt.Horizontal); self.speed.setRange(3, 30); self.speed.setValue(int(a["mouse_speed"] * 10))
        self.typing = QComboBox()
        for lab, k in (("Automatic", "auto"), ("Always type keys", "type"), ("Always paste (clipboard)", "paste")):
            self.typing.addItem(lab, k)
        self.typing.setCurrentIndex(self.typing.findData(a["typing_mode"]))
        self.confirm = QCheckBox("Ask me before risky actions"); self.confirm.setChecked(a["confirm_risky"])
        self.minimize = QCheckBox("Hide the chat window while a task runs"); self.minimize.setChecked(a["minimize_on_task"])
        self.grid = QCheckBox("Draw a coordinate grid on screenshots (helps pointing accuracy)"); self.grid.setChecked(a["grid_overlay"])
        f.addRow("Max steps per task", self.max_steps)
        f.addRow("Retries per step", self.retries)
        f.addRow("Wait after each action", self.delay)
        f.addRow("Mouse speed", self.speed)
        f.addRow("Typing", self.typing)
        for c in (self.verify, self.human, self.confirm, self.minimize, self.grid):
            f.addRow(c)
        self.tabs.addTab(_scroll(w), "Agent")

        # ---------------- Capture + voice
        c, v = d["capture"], d["voice"]
        w, f = _form()
        self.maxdim = QSpinBox(); self.maxdim.setRange(640, 3840); self.maxdim.setSingleStep(160); self.maxdim.setValue(c["max_dimension"])
        self.jpeg = QSpinBox(); self.jpeg.setRange(30, 95); self.jpeg.setValue(c["jpeg_quality"])
        self.hide_mode = QComboBox()
        for lab, k in (("Automatic (hide only if needed)", "auto"), ("Always hide windows while capturing", "always"),
                       ("Never hide", "never")):
            self.hide_mode.addItem(lab, k)
        self.hide_mode.setCurrentIndex(self.hide_mode.findData(c["hide_mode"]))
        f.addRow("Screenshot max size (px)", self.maxdim)
        f.addRow("JPEG quality", self.jpeg)
        f.addRow("Hide this app in screenshots", self.hide_mode)
        lbl = QLabel("Voice input"); lbl.setObjectName("section"); f.addRow(lbl)
        self.engine = QComboBox()
        for lab, k in (("Google web speech (free)", "google"), ("OpenAI Whisper (needs OpenAI key)", "openai"),
                       ("Gemini (needs Gemini key)", "gemini")):
            self.engine.addItem(lab, k)
        self.engine.setCurrentIndex(self.engine.findData(v["engine"]))
        self.vlang = QLineEdit(v["language"]); self.vlang.setPlaceholderText("en-US, en-IN, hi-IN, ta-IN …")
        self.silence = QDoubleSpinBox(); self.silence.setRange(0.6, 5.0); self.silence.setSingleStep(0.2); self.silence.setValue(v["silence_seconds"])
        self.silence.setSuffix(" s")
        self.autosend = QCheckBox("Send automatically after speaking"); self.autosend.setChecked(v["auto_send"])
        f.addRow("Engine", self.engine)
        f.addRow("Speech language", self.vlang)
        f.addRow("Stop after silence", self.silence)
        f.addRow(self.autosend)
        self.tabs.addTab(_scroll(w), "Screen & voice")

        # ---------------- Hotkeys + look
        h, u = d["hotkeys"], d["ui"]
        w, f = _form()
        self.hk = {}
        for key, label in (("summarize", "Summarize screen now"), ("toggle_window", "Show / hide window"),
                           ("stop_agent", "Stop running task"), ("voice", "Start voice command")):
            e = QLineEdit(h[key]); self.hk[key] = e
            f.addRow(label, e)
        hint = QLabel("Format: <ctrl>+<alt>+s   ·   modifiers: <ctrl> <alt> <shift> <cmd>   ·   special keys in <>")
        hint.setObjectName("muted"); hint.setWordWrap(True); f.addRow(hint)
        lbl = QLabel("Appearance"); lbl.setObjectName("section"); f.addRow(lbl)
        self.opacity = QSlider(Qt.Horizontal); self.opacity.setRange(40, 100); self.opacity.setValue(int(u["opacity"] * 100))
        self.blur = QCheckBox("Frosted-glass blur (Windows, restart needed)"); self.blur.setChecked(u["native_blur"])
        self.tray = QCheckBox("Show tray icon"); self.tray.setChecked(u["show_tray"])
        self.hidden = QCheckBox("Start hidden (use the hotkey to open)"); self.hidden.setChecked(u["start_hidden"])
        f.addRow("Glass opacity", self.opacity)
        for c_ in (self.blur, self.tray, self.hidden):
            f.addRow(c_)
        self.tabs.addTab(_scroll(w), "Hotkeys & look")

        self.error = QLabel("")
        self.error.setStyleSheet("color:#FCA5A5;")
        self.error.setWordWrap(True)
        self.body_layout.addWidget(self.error)
        row = QHBoxLayout()
        cancel = button("Cancel"); cancel.clicked.connect(self.hide)
        save = button("Save", "primary"); save.clicked.connect(self._save)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(save); row.addSpacing(18)
        self.body_layout.addLayout(row)

    # ------------------------------------------------------------------
    def _test(self, key: str):
        api, model, base, res = self.pw[key]
        res.setText("Testing…")
        k = api.text().strip() or self.ctl.cfg.api_key(key)

        def job():
            try:
                reply = PROVIDERS[key](k, model.currentText().strip(), base.text().strip(), 40).ping()
                self._test_result.emit(f"{key}|Connected – model replied “{reply.strip()[:30]}”", True)
            except (LLMError, Exception) as e:
                self._test_result.emit(f"{key}|Connection failed: {e}", False)
        threading.Thread(target=job, daemon=True).start()

    def _on_test(self, msg: str, ok: bool):
        key, text = msg.split("|", 1)
        self.pw[key][3].setText(text)

    def _save(self):
        for k, e in self.hk.items():
            if not HotkeyManager.validate(e.text().strip()):
                self.error.setText(f"Invalid hotkey “{e.text()}”. Example: <ctrl>+<alt>+s")
                return
        d = self.ctl.cfg.data
        d["provider"] = self.provider.currentData()
        d["language"] = self.language.text().strip() or "English"
        for key, (api, model, base, _) in self.pw.items():
            d["providers"][key].update(api_key=api.text().strip(), model=model.currentText().strip(),
                                       base_url=base.text().strip().rstrip("/"))
        d["agent"].update(max_steps=self.max_steps.value(), verify_each_step=self.verify.isChecked(),
                          max_retries=self.retries.value(), post_action_delay=self.delay.value(),
                          human_like=self.human.isChecked(), mouse_speed=self.speed.value() / 10,
                          typing_mode=self.typing.currentData(), confirm_risky=self.confirm.isChecked(),
                          minimize_on_task=self.minimize.isChecked(), grid_overlay=self.grid.isChecked())
        d["capture"].update(max_dimension=self.maxdim.value(), jpeg_quality=self.jpeg.value(),
                            hide_mode=self.hide_mode.currentData())
        d["voice"].update(engine=self.engine.currentData(), language=self.vlang.text().strip() or "en-US",
                          silence_seconds=self.silence.value(), auto_send=self.autosend.isChecked())
        for k, e in self.hk.items():
            d["hotkeys"][k] = e.text().strip()
        d["ui"].update(opacity=self.opacity.value() / 100, native_blur=self.blur.isChecked(),
                       show_tray=self.tray.isChecked(), start_hidden=self.hidden.isChecked())
        self.ctl.cfg.save()
        self.saved.emit()
        self.hide()
