STYLE_SHEET = """
QWidget {
    background: #070707;
    color: #d8d8d8;
    font-family: "DejaVu Sans Mono";
    font-size: 12px;
}
QFrame#topBar {
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121212, stop:1 #202020);
}
QPushButton#topTab {
    background: #161616;
    border: 1px solid #2e2e2e;
    border-radius: 5px;
    padding: 8px 16px;
    color: #8e8e8e;
    font-weight: bold;
}
QPushButton#topTab:checked {
    color: #f0f0f0;
    border-color: #2aa43b;
    background: #0f180f;
}
QPushButton#subTab {
    background: transparent;
    border: 0px;
    color: #6f6f6f;
    padding: 4px 8px;
}
QPushButton#subTab:checked {
    color: #f0f0f0;
}
QLabel#brand {
    color: #29c449;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 3px;
}
QFrame#bodyFrame {
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    background: #060606;
}
QFrame#leftPanel {
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    background: #101010;
}
QLabel#statusLabel {
    color: #5de26b;
}
QLabel#pageTitle {
    color: #f0f0f0;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 1px;
}
QFrame#keyboardFrame, QFrame#mouseListPanel, QFrame#mouseVisual {
    border: 1px solid #1f1f1f;
    border-radius: 10px;
    background: #0d0d0d;
}
QPushButton#keyButton {
    background: #121212;
    border: 1px solid #2b2b2b;
    border-radius: 4px;
    color: #f0f0f0;
}
QPushButton#keyButton[mapped="true"] {
    border: 1px solid #2ac64f;
    color: #2de25a;
    background: #101c10;
}
QPushButton#mouseMapButton, QPushButton#mouseNode {
    background: #111111;
    border: 1px solid #2c2c2c;
    border-radius: 6px;
    color: #f0f0f0;
    padding: 6px;
}
QLabel#mouseBadge {
    border: 1px solid #2ac64f;
    border-radius: 11px;
    min-height: 22px;
    max-height: 22px;
    text-align: center;
    qproperty-alignment: AlignCenter;
    color: #2ac64f;
}
QLabel#hintLabel {
    color: #8f8f8f;
}
QFrame#deviceDock {
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111111, stop:1 #171717);
}
QPushButton {
    background: #171717;
    border: 1px solid #303030;
    border-radius: 6px;
    padding: 6px 10px;
}
QPushButton:hover {
    border-color: #3d3d3d;
}
QLineEdit, QComboBox {
    background: #0d0d0d;
    border: 1px solid #2b2b2b;
    border-radius: 5px;
    padding: 5px;
}
"""
