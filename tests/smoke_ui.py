"""Headless UI smoke test:  QT_QPA_PLATFORM=offscreen python tests/smoke_ui.py"""
import os, sys, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
import tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
from agent.config import Config
from ui.theme import stylesheet
from ui.app_controller import AppController
app.setStyleSheet(stylesheet())
cfg = Config({}, Path(tempfile.mkdtemp()) / "c.json")
ctl = AppController(app, cfg)
ctl.show_initial()
ctl.status.show()
ctl.main.set_mode(1)
ctl.bridge.log("capture", "hello"); ctl.bridge.set_state("thinking", "x"); ctl.bridge.say("hi there")
ctl.main.agent_page.chat.add("user", "send leave email to ramesh@gmail.com")
ctl.open_settings()
ctl.settings_win._save()   # should save without errors
ctl.main.sum_page._on_failed("no key")
for i in range(5): app.processEvents(); time.sleep(0.05)
# render windows to images to prove painting works
for name, w in (("main", ctl.main), ("status", ctl.status)):
    w.grab().save(f"/tmp/{name}.png")
print("native excluded flag:", ctl.registry.all_excluded, "| needs_hide:", ctl.registry.needs_hide())
print("UI SMOKE OK; saved:", cfg.path.exists())
