from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def build_app_icon(size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#00000000"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Frame
    painter.setPen(QPen(QColor("#1f1f1f"), 2))
    painter.setBrush(QColor("#0b0b0b"))
    painter.drawRoundedRect(QRect(4, 4, size - 8, size - 8), 10, 10)

    # Keyboard block
    painter.setPen(QPen(QColor("#2a2a2a"), 1))
    painter.setBrush(QColor("#131313"))
    painter.drawRoundedRect(QRect(10, 14, size - 20, 28), 6, 6)

    painter.setPen(QPen(QColor("#1fc94f"), 1))
    for row in range(2):
        for col in range(6):
            x = 14 + col * 8
            y = 18 + row * 10
            painter.drawRect(QRect(x, y, 6, 6))

    # Mouse wheel accent
    painter.setBrush(QColor("#1a1a1a"))
    painter.setPen(QPen(QColor("#2a2a2a"), 1))
    painter.drawRoundedRect(QRect(size // 2 - 6, 44, 12, 14), 6, 6)
    painter.setBrush(QColor("#1fc94f"))
    painter.setPen(QPen(QColor("#1fc94f"), 1))
    painter.drawRoundedRect(QRect(size // 2 - 2, 47, 4, 6), 2, 2)

    painter.end()
    return QIcon(pixmap)
