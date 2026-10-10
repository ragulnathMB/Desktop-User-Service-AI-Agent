from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
import qtawesome as qta

from .theme import ACCENT, ACCENT2


def make_icon(name: str, color: str = "#EEF2FF") -> QIcon:
    return qta.icon(name, color=color)


def make_pixmap(size: int = 64) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(ACCENT))
    g.setColorAt(1, QColor(ACCENT2))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(size * .06, size * .06, size * .88, size * .88), size * .28, size * .28)
    # four-point sparkle
    c, r = size / 2, size * .26
    path = QPainterPath()
    path.moveTo(c, c - r)
    path.quadTo(c, c, c + r, c)
    path.quadTo(c, c, c, c + r)
    path.quadTo(c, c, c - r, c)
    path.quadTo(c, c, c, c - r)
    p.setBrush(QColor(11, 16, 32))
    p.drawPath(path)
    p.setBrush(QColor(255, 255, 255, 200))
    p.drawEllipse(QPointF(size * .74, size * .27), size * .05, size * .05)
    p.end()
    return pm


def make_app_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128):
        icon.addPixmap(make_pixmap(s))
    return icon
