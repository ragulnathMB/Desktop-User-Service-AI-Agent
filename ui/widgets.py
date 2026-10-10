from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget)


def button(text: str, variant: str | None = None, tip: str | None = None) -> QPushButton:
    b = QPushButton(text)
    if variant:
        b.setProperty("variant", variant)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


def repolish(w: QWidget):
    w.style().unpolish(w)
    w.style().polish(w)


class ModeSwitch(QWidget):
    changed = Signal(int)

    def __init__(self, labels: list[str]):
        super().__init__()
        self.setObjectName("segBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for i, t in enumerate(labels):
            b = QPushButton(t)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b, 1)
            self.buttons.append(b)
        self.group.idClicked.connect(self.changed.emit)

    def set_index(self, i: int):
        self.buttons[i].setChecked(True)


class ChatView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._box = QWidget()
        self._lay = QVBoxLayout(self._box)
        self._lay.setContentsMargins(2, 4, 2, 4)
        self._lay.setSpacing(8)
        self._lay.addStretch(1)
        self.setWidget(self._box)
        self._bubbles: list[QLabel] = []

    def add(self, role: str, text: str):
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.PlainText)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            lab.setObjectName("bubbleUser")
            row.addStretch(1)
            row.addWidget(lab)
        elif role == "system":
            lab.setObjectName("bubbleSys")
            lab.setAlignment(Qt.AlignCenter)
            row.addWidget(lab, 1)
        else:
            lab.setObjectName("bubbleBot")
            row.addWidget(lab)
            row.addStretch(1)
        self._lay.insertLayout(self._lay.count() - 1, row)
        self._bubbles.append(lab)
        self._fit(lab)
        QTimer.singleShot(40, self._to_bottom)

    def _fit(self, lab: QLabel):
        if lab.objectName() != "bubbleSys":
            lab.setMaximumWidth(max(180, int(self.viewport().width() * 0.84)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for b in self._bubbles:
            self._fit(b)

    def _to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
