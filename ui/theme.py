"""Glass theme: colours + global Qt stylesheet."""
ACCENT = "#8B7BFF"
ACCENT2 = "#2DD4F0"
TEXT = "#EEF2FF"
MUTED = "#9AA4C7"

STATE_COLORS = {
    "idle": "#94A3B8", "capturing": "#2DD4F0", "thinking": "#A78BFA", "acting": "#38BDF8",
    "verifying": "#FBBF24", "waiting": "#F472B6", "error": "#F87171", "done": "#4ADE80",
}
STATE_LABELS = {
    "idle": "Idle", "capturing": "Capturing", "thinking": "Thinking", "acting": "Acting",
    "verifying": "Verifying", "waiting": "Needs you", "error": "Problem", "done": "Done",
}
LEVELS = {
    "info": ("mdi6.information-outline", "#B8C2E6"), "capture": ("mdi6.camera", "#67E8F9"),
    "llm": ("mdi6.brain", "#C4B5FD"), "action": ("mdi6.cursor-default-click", "#7DD3FC"),
    "verify": ("mdi6.magnify", "#FDE68A"), "ok": ("mdi6.check-circle", "#86EFAC"),
    "warn": ("mdi6.alert-outline", "#FCD34D"), "error": ("mdi6.alert-circle", "#FCA5A5"),
    "user": ("mdi6.account", "#F9A8D4"),
}

_QSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 13px; color: %TEXT%; outline: none; }
QToolTip { background: #1B2036; color: %TEXT%; border: 1px solid rgba(255,255,255,40); padding: 5px 8px; border-radius: 6px; }
QLabel { background: transparent; }
QLabel#muted { color: %MUTED%; font-size: 12px; }
QLabel#title { font-size: 14px; font-weight: 600; }
QLabel#section { font-size: 12px; font-weight: 600; color: %MUTED%; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: rgba(255,255,255,18); border: 1px solid rgba(255,255,255,36);
    border-radius: 10px; padding: 7px 10px; selection-background-color: %ACCENT%; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid %ACCENT%; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #1B2036; border: 1px solid rgba(255,255,255,40);
    selection-background-color: %ACCENT%; outline: 0; padding: 4px; }

QPushButton { background: rgba(255,255,255,22); border: 1px solid rgba(255,255,255,40);
    border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { background: rgba(255,255,255,40); }
QPushButton:pressed { background: rgba(255,255,255,14); }
QPushButton:disabled { color: #6B7394; background: rgba(255,255,255,10); }
QPushButton[variant="primary"] { border: none; color: #0B1020; font-weight: 600;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 %ACCENT%, stop:1 %ACCENT2%); }
QPushButton[variant="primary"]:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #A094FF, stop:1 #5EE3F7); }
QPushButton[variant="danger"] { background: rgba(248,113,113,70); border: 1px solid rgba(248,113,113,150); }
QPushButton[variant="danger"]:hover { background: rgba(248,113,113,120); }
QPushButton[variant="rec"] { background: rgba(248,113,113,150); border: 1px solid #F87171; }
QPushButton#seg { background: transparent; border: none; border-radius: 12px; padding: 9px 12px; color: %MUTED%; font-weight: 600; }
QPushButton#seg:hover { color: %TEXT%; }
QPushButton#seg:checked { color: #0B1020;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 %ACCENT%, stop:1 %ACCENT2%); }
QWidget#segBar { background: rgba(255,255,255,16); border: 1px solid rgba(255,255,255,30); border-radius: 15px; }
QToolButton#tbtn, QToolButton#tbtn_close { background: transparent; border: none; border-radius: 8px; padding: 4px 9px; font-size: 14px; color: %MUTED%; }
QToolButton#tbtn:hover, QToolButton#tbtn_close:hover { background: rgba(255,255,255,40); color: %TEXT%; }
QToolButton#tbtn_close:hover { background: rgba(248,113,113,190); color: white; }

QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid rgba(255,255,255,90); background: rgba(255,255,255,15); }
QCheckBox::indicator:checked { background: %ACCENT%; border: 1px solid %ACCENT%; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,60); border-radius: 3px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,110); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0; }

QTextBrowser, QTextEdit { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,28);
    border-radius: 12px; padding: 6px; selection-background-color: %ACCENT%; }

QTabWidget::pane { border: none; }
QTabBar::tab { background: rgba(255,255,255,14); border-radius: 9px; padding: 6px 12px; margin: 0 4px 8px 0; color: %MUTED%; }
QTabBar::tab:selected { background: rgba(139,123,255,130); color: white; }

QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,40); border-radius: 2px; }
QSlider::handle:horizontal { background: %ACCENT%; width: 14px; margin: -6px 0; border-radius: 7px; }
QSlider::sub-page:horizontal { background: %ACCENT%; border-radius: 2px; }

QLabel#bubbleUser { color: #0B1020; border-radius: 14px; padding: 9px 13px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 %ACCENT%, stop:1 %ACCENT2%); }
QLabel#bubbleBot { background: rgba(255,255,255,24); border: 1px solid rgba(255,255,255,36);
    border-radius: 14px; padding: 9px 13px; }
QLabel#bubbleSys { color: %MUTED%; font-size: 12px; }
QLabel#pill { border-radius: 11px; padding: 3px 12px; font-weight: 600; }
QWidget#card { background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,28); border-radius: 14px; }
"""

MD_CSS = ("h1,h2,h3{color:#C4B5FD;} p{margin:4px 0;} li{margin-bottom:4px;} "
          "code{background:#232a48;color:#7DD3FC;} b,strong{color:#FFFFFF;}")


def stylesheet() -> str:
    return (_QSS.replace("%ACCENT2%", ACCENT2).replace("%ACCENT%", ACCENT)
            .replace("%TEXT%", TEXT).replace("%MUTED%", MUTED))
