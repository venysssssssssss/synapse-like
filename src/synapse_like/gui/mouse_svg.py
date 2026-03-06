from __future__ import annotations

from typing import Dict, Iterable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


MOUSE_BUTTON_BOUNDS = {
    "LMB": QRectF(45, 25, 65, 110),
    "RMB": QRectF(110, 25, 65, 110),
    "MMB": QRectF(92, 35, 16, 45),
    "M4": QRectF(18, 156, 24, 34),
    "M5": QRectF(18, 198, 24, 34),
}

MOUSE_SVG = """<svg viewBox="0 0 220 320" xmlns="http://www.w3.org/2000/svg">
<style>
.base { fill: #101010; stroke: #2a2a2a; stroke-width: 2; }
.button { fill: #191919; stroke: #2d2d2d; stroke-width: 1.5; }
</style>
<path class="base" d="M45,80 C45,18 175,18 175,80 L175,250 C175,300 45,300 45,250 Z"/>
<path id="LMB" class="button" d="M45,80 C45,26 108,26 108,80 L108,135 L45,135 Z"/>
<path id="RMB" class="button" d="M112,80 C112,26 175,26 175,80 L175,135 L112,135 Z"/>
<rect id="MMB" class="button" x="92" y="35" width="16" height="45" rx="5"/>
<rect id="M4" class="button" x="18" y="156" width="24" height="34" rx="4"/>
<rect id="M5" class="button" x="18" y="198" width="24" height="34" rx="4"/>
</svg>"""


class MouseSvgWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer(MOUSE_SVG.encode("utf-8"))
        self._hovered_button = ""
        self._active_codes: set[str] = set()
        self._mapped_buttons: set[str] = set()
        self._tooltips: Dict[str, str] = {}
        self.setMouseTracking(True)
        self.setMinimumSize(260, 340)

    def set_active_keys(self, keys: Iterable[str]) -> None:
        self._active_codes = set(keys)
        self.update()

    def set_mapped_buttons(self, labels: Iterable[str]) -> None:
        self._mapped_buttons = set(labels)
        self.update()

    def set_tooltip_map(self, tooltips: Dict[str, str]) -> None:
        self._tooltips = dict(tooltips)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        target = self.rect().adjusted(10, 10, -10, -10)
        self._renderer.render(painter, target)
        scale_x = target.width() / 220.0
        scale_y = target.height() / 320.0
        painter.translate(target.left(), target.top())
        painter.scale(scale_x, scale_y)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(68, 214, 44, 45))
        for label in self._mapped_buttons:
            rect = MOUSE_BUTTON_BOUNDS.get(label)
            if rect:
                painter.drawRoundedRect(rect, 8, 8)

        painter.setBrush(QColor(68, 214, 44, 120))
        for label, code in {
            "LMB": "BTN_LEFT",
            "RMB": "BTN_RIGHT",
            "MMB": "BTN_MIDDLE",
            "M4": "BTN_SIDE",
            "M5": "BTN_EXTRA",
        }.items():
            if code not in self._active_codes:
                continue
            rect = MOUSE_BUTTON_BOUNDS.get(label)
            if rect:
                painter.drawRoundedRect(rect, 8, 8)

        if self._hovered_button:
            rect = MOUSE_BUTTON_BOUNDS.get(self._hovered_button)
            if rect:
                painter.setPen(QPen(QColor("#72ff58"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect, 8, 8)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        button = self._button_at(event.position().x(), event.position().y())
        if button != self._hovered_button:
            self._hovered_button = button
            self.setToolTip(self._tooltips.get(button, button) if button else "")
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hovered_button:
            self._hovered_button = ""
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        button = self._button_at(event.position().x(), event.position().y())
        if button:
            self.clicked.emit(button)

    def _button_at(self, x: float, y: float) -> str:
        target = self.rect().adjusted(10, 10, -10, -10)
        if not target.contains(x, y):
            return ""
        svg_x = (x - target.left()) * 220.0 / max(target.width(), 1)
        svg_y = (y - target.top()) * 320.0 / max(target.height(), 1)
        for label, rect in MOUSE_BUTTON_BOUNDS.items():
            if rect.contains(svg_x, svg_y):
                return label
        return ""
