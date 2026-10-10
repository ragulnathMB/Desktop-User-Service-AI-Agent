"""Frameless translucent 'glass' window base class."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizeGrip, QToolButton, QVBoxLayout, QWidget

from .icons import make_icon, make_pixmap

RADIUS = 22


class TitleBar(QWidget):
    def __init__(self, title: str, window: "GlassWindow"):
        super().__init__(window)
        self._win = window
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 10, 4)
        lay.setSpacing(2)
        logo = QLabel()
        logo.setPixmap(make_pixmap(40).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(logo)
        lay.addSpacing(6)
        self.title = QLabel(title)
        self.title.setObjectName("title")
        lay.addWidget(self.title)
        lay.addStretch(1)
        self._extra = lay
        self._btn_index = lay.count()
        self.btn_min = self._mk("", "Hide", window.hide)
        self.btn_min.setIcon(make_icon("mdi6.minus"))
        self.btn_close = self._mk("", "Hide to tray", window.hide, "tbtn_close")
        self.btn_close.setIcon(make_icon("mdi6.close"))

    def _mk(self, text, tip, slot, name="tbtn"):
        b = QToolButton()
        b.setObjectName(name)
        b.setText(text)
        if not text:
            b.setIconSize(QSize(16, 16))
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        self.layout().addWidget(b)
        return b

    def add_button(self, text, tip, slot):
        b = QToolButton()
        b.setObjectName("tbtn")
        b.setText(text)
        if not text:
            b.setIconSize(QSize(16, 16))
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        self.layout().insertWidget(self._btn_index, b)
        self._btn_index += 1
        return b

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            h = self._win.windowHandle()
            if h:
                h.startSystemMove()
        super().mousePressEvent(e)


class GlassWindow(QWidget):
    """Top-level tool window: no taskbar button, translucent, rounded, draggable, resizable."""

    def __init__(self, registry, cfg, title: str, size=(460, 640), min_size=(360, 420), on_top=True):
        super().__init__()
        self.registry, self.cfg = registry, cfg
        flags = Qt.FramelessWindowHint | Qt.Tool
        if on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setWindowTitle(title)
        self.resize(*size)
        self.setMinimumSize(*min_size)
        self._blur = False
        self._native_done = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.titlebar = TitleBar(title, self)
        outer.addWidget(self.titlebar)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 6, 16, 12)
        self.body_layout.setSpacing(10)
        outer.addWidget(self.body, 1)
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)

    # ------------------------------------------------------------ native
    def set_blur_active(self, on: bool):
        self._blur = on
        self._update_mask()
        self.update()

    def _update_mask(self):
        if self._blur:
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
            self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        else:
            self.clearMask()

    def showEvent(self, e):
        super().showEvent(e)
        if not self._native_done:
            self._native_done = True
            QTimer.singleShot(0, lambda: self.registry.apply(self))

    def show_front(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - 18, self.height() - 18)
        self._update_mask()

    # ------------------------------------------------------------- paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        path = QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        a = float(self.cfg.data["ui"]["opacity"])
        alpha = int(255 * a * (0.62 if self._blur else 1.0))
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, QColor(40, 44, 78, alpha))
        g.setColorAt(1.0, QColor(14, 18, 36, alpha))
        p.fillPath(path, g)
        sheen = QLinearGradient(QPointF(r.left(), r.top()), QPointF(r.left(), r.top() + r.height() * .32))
        sheen.setColorAt(0, QColor(255, 255, 255, 40))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(path, sheen)
        edge = QLinearGradient(r.topLeft(), r.bottomRight())
        edge.setColorAt(0, QColor(255, 255, 255, 90))
        edge.setColorAt(1, QColor(255, 255, 255, 18))
        p.setPen(QPen(edge, 1.2))
        p.drawPath(path)
