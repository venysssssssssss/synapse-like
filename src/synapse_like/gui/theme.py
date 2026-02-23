# Colors
c_bg_dark = "#0a0a0a"       # Main background
c_bg_panel = "#121212"      # Panel/Card background
c_bg_input = "#050505"      # Inputs background
c_primary = "#44d62c"       # Razer Green
c_primary_hover = "#55eb3d"
c_primary_dim = "#2a8a1c"
c_text_main = "#ffffff"
c_text_sec = "#888888"
c_border = "#2a2a2a"
c_border_hover = "#444444"
c_danger = "#d62c2c"

STYLE_SHEET = f"""
/* GLOBAL RESET */
* {{
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: {c_text_main};
    selection-background-color: {c_primary_dim};
    selection-color: #ffffff;
    outline: none;
}}

QWidget {{
    background-color: {c_bg_dark};
}}

/* SCROLLBARS */
QScrollBar:vertical {{
    border: none;
    background: {c_bg_dark};
    width: 8px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: #333;
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

/* TOP BAR */
QFrame#topBar {{
    background-color: {c_bg_dark};
    border-bottom: 1px solid {c_border};
}}

QPushButton#topTab {{
    background-color: transparent;
    color: {c_text_sec};
    font-weight: 600;
    font-size: 14px;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    margin: 0 4px;
}}
QPushButton#topTab:hover {{
    color: #cccccc;
}}
QPushButton#topTab:checked {{
    color: {c_primary};
    border-bottom: 2px solid {c_primary};
}}

QLabel#brand {{
    color: {c_primary};
    font-size: 18px;
    font-weight: 900;
    letter-spacing: 1px;
    font-family: "Arial Black", sans-serif; 
}}

QPushButton#subTab {{
    background-color: transparent;
    color: {c_text_sec};
    font-size: 12px;
    border: none;
    padding: 6px 12px;
}}
QPushButton#subTab:checked {{
    color: #ffffff;
    font-weight: bold;
}}

/* BODY & LAYOUT */
QFrame#leftPanel {{
    background-color: {c_bg_dark};
    border-right: 1px solid {c_border};
}}

/* PAGE TITLES */
QLabel#pageTitle {{
    color: {c_text_main};
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 0.5px;
    padding: 8px 0;
}}

/* CARDS (Left Panel) */
QFrame[class="card"] {{
    background-color: {c_bg_panel};
    border: 1px solid {c_border};
    border-radius: 6px;
}}
QLabel[class="cardTitle"] {{
    color: {c_primary};
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLabel[class="fieldLabel"] {{
    color: {c_text_sec};
    font-size: 11px;
    margin-top: 4px;
}}

/* INPUTS */
QLineEdit, QComboBox {{
    background-color: {c_bg_input};
    border: 1px solid {c_border};
    border-radius: 4px;
    padding: 6px;
    color: #eeeeee;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {c_primary_dim};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c_text_sec};
    margin-right: 6px;
}}

QCheckBox {{
    spacing: 8px;
    color: {c_text_sec};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    background-color: {c_bg_input};
    border: 1px solid {c_border};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background-color: {c_primary_dim};
    border: 1px solid {c_primary};
    image: none;
}}

/* BUTTONS */
QPushButton {{
    background-color: {c_bg_panel};
    border: 1px solid {c_border};
    border-radius: 4px;
    padding: 8px 12px;
    color: #e0e0e0;
}}
QPushButton:hover {{
    background-color: #1a1a1a;
    border-color: {c_border_hover};
}}
QPushButton:pressed {{
    background-color: #050505;
}}

/* Primary Action Button */
QPushButton[class="primaryBtn"] {{
    background-color: {c_primary_dim};
    border: 1px solid {c_primary_dim};
    color: #ffffff;
    font-weight: bold;
}}
QPushButton[class="primaryBtn"]:hover {{
    background-color: {c_primary};
    border: 1px solid {c_primary};
    color: #000000;
}}

/* Danger Button */
QPushButton[class="dangerBtn"] {{
    background-color: transparent;
    border: 1px solid {c_danger};
    color: {c_danger};
}}
QPushButton[class="dangerBtn"]:hover {{
    background-color: {c_danger};
    color: #ffffff;
}}

/* Secondary / Icon Buttons */
QPushButton[class="secondaryBtn"] {{
    background-color: transparent;
    border: 1px solid {c_border};
}}
QPushButton[class="iconBtn"] {{
    background-color: {c_bg_input};
    border: 1px solid {c_border};
    padding: 4px;
    min-width: 20px;
}}

/* KEYBOARD MAPPER GRID */
QFrame#keyboardFrame {{
    background-color: {c_bg_panel};
    border: 1px solid {c_border};
    border-radius: 8px;
}}
QPushButton#keyButton {{
    background-color: #0f0f0f;
    border: 1px solid #222;
    border-radius: 4px;
    color: {c_text_sec};
    font-size: 11px;
    font-weight: bold;
}}
QPushButton#keyButton:hover {{
    border-color: {c_primary_dim};
    color: #fff;
}}
QPushButton#keyButton[mapped="true"] {{
    background-color: #0b1a0b;
    border: 1px solid {c_primary_dim};
    color: {c_primary};
}}

/* DEVICE DOCK (Bottom) */
QFrame#deviceDock {{
    background-color: {c_bg_panel};
    border-top: 1px solid {c_border};
}}
QFrame#deviceCard {{
    background-color: {c_bg_input};
    border: 1px solid {c_border};
    border-radius: 4px;
}}
QFrame#deviceCard:hover {{
    border: 1px solid {c_primary_dim};
}}

/* STATUS LABEL */
QLabel#statusLabel {{
    color: {c_text_sec};
    font-style: italic;
    font-size: 11px;
}}

/* MOUSE PAGE */
QFrame#mouseListPanel, QFrame#mouseVisual {{
    background-color: {c_bg_panel};
    border: 1px solid {c_border};
    border-radius: 8px;
}}
QLabel#mouseBadge {{
    background-color: {c_bg_input};
    border: 1px solid {c_primary_dim};
    color: {c_primary};
    border-radius: 11px; 
    font-weight: bold;
    qproperty-alignment: AlignCenter;
}}
"""
