from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from synapse_like.gui.constants import KEYBOARD_LAYOUT, KEYMAP


@dataclass(slots=True)
class KeyShape:
    label: str
    code: str
    rect: QRectF


class KeyboardSvgWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shapes = self._build_shapes()
        self._bounds = {shape.code: shape.rect for shape in self._shapes}
        self._tooltips: Dict[str, str] = {}
        self._hovered_code = ""
        self._active_codes: set[str] = set()
        self._mapped_codes: set[str] = set()
        self._renderer = QSvgRenderer(self._render_svg().encode("utf-8"))
        self.setMouseTracking(True)
        self.setMinimumSize(960, 320)

    def set_active_keys(self, keys: Iterable[str]) -> None:
        normalized = set(keys)
        if normalized != self._active_codes:
            self._active_codes = normalized
            self.update()

    def set_mapped_keys(self, keys: Iterable[str]) -> None:
        self._mapped_codes = set(keys)
        self.update()

    def set_tooltip_map(self, tooltips: Dict[str, str]) -> None:
        self._tooltips = dict(tooltips)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        target = self.rect().adjusted(10, 10, -10, -10)
        self._renderer.render(painter, target)

        scale_x = target.width() / 1020.0
        scale_y = target.height() / 420.0
        painter.translate(target.left(), target.top())
        painter.scale(scale_x, scale_y)

        if self._mapped_codes:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(68, 214, 44, 45))
            for code in self._mapped_codes:
                rect = self._bounds.get(code)
                if rect:
                    painter.drawRoundedRect(rect, 10, 10)

        if self._active_codes:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(68, 214, 44, 120))
            for code in self._active_codes:
                rect = self._bounds.get(code)
                if rect:
                    painter.drawRoundedRect(rect, 10, 10)

        if self._hovered_code:
            rect = self._bounds.get(self._hovered_code)
            if rect:
                painter.setPen(QPen(QColor("#72ff58"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect, 10, 10)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        code = self._code_at(event.position().x(), event.position().y())
        if code != self._hovered_code:
            self._hovered_code = code
            if code:
                self.setToolTip(self._tooltips.get(code, code))
            else:
                self.setToolTip("")
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hovered_code:
            self._hovered_code = ""
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        code = self._code_at(event.position().x(), event.position().y())
        if code:
            self.clicked.emit(code)

    def _code_at(self, x: float, y: float) -> str:
        target = self.rect().adjusted(10, 10, -10, -10)
        if not target.contains(x, y):
            return ""
        svg_x = (x - target.left()) * 1020.0 / max(target.width(), 1)
        svg_y = (y - target.top()) * 420.0 / max(target.height(), 1)
        for shape in self._shapes:
            if shape.rect.contains(svg_x, svg_y):
                return shape.code
        return ""

    def _build_shapes(self) -> list[KeyShape]:
        shapes: list[KeyShape] = []
        key_width = 56.0
        key_height = 50.0
        horizontal_gap = 6.0
        vertical_gap = 10.0
        start_y = 20.0
        for row_index, row in enumerate(KEYBOARD_LAYOUT):
            cursor_x = 20.0
            cursor_y = start_y + row_index * (key_height + vertical_gap)
            for label, width_units in row:
                width = width_units * key_width + (width_units - 1) * horizontal_gap
                rect = QRectF(cursor_x, cursor_y, width, key_height)
                shapes.append(KeyShape(label=label, code=KEYMAP.get(label, label), rect=rect))
                cursor_x += width + horizontal_gap
        return shapes

    def _render_svg(self) -> str:
        parts = [
            '<svg viewBox="0 0 1020 420" xmlns="http://www.w3.org/2000/svg">',
            "<style>",
            ".key { fill: #121212; stroke: #2a2a2a; stroke-width: 1.8; }",
            ".label { fill: #9ca3af; font-family: Arial, sans-serif; font-size: 14px; }",
            "</style>",
        ]
        for shape in self._shapes:
            rect = shape.rect
            parts.append(
                f'<rect id="{shape.code}" class="key" x="{rect.x():.1f}" y="{rect.y():.1f}" '
                f'width="{rect.width():.1f}" height="{rect.height():.1f}" rx="10" ry="10"/>'
            )
            parts.append(
                f'<text class="label" x="{rect.x() + 10:.1f}" y="{rect.y() + 28:.1f}">{shape.label}</text>'
            )
        parts.append("</svg>")
        return "".join(parts)
