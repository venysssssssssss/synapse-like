from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

from synapse_like.remap.actions import Action, ActionType


class ActionDialog(QDialog):
    def __init__(self, key_label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Atribuir acao: {key_label}")

        layout = QVBoxLayout()

        self.combo = QComboBox()
        self.combo.addItems(
            [
                "Pass-through (default)",
                "Remap to key",
                "Scroll up",
                "Scroll down",
                "Mouse button X1",
                "Mouse button X2",
            ]
        )
        self.combo.currentIndexChanged.connect(self._on_mode_changed)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Ex: KEY_A")
        self.key_input.setVisible(False)

        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancelar")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)

        layout.addWidget(self.combo)
        layout.addWidget(self.key_input)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _on_mode_changed(self, idx: int):
        self.key_input.setVisible(idx == 1)

    def get_action(self) -> Action:
        idx = self.combo.currentIndex()
        if idx == 0:
            return Action(ActionType.NONE)
        if idx == 1:
            target = self.key_input.text().strip().upper() or "KEY_A"
            return Action(ActionType.KEYSTROKE, {"key": target})
        if idx == 2:
            return Action(ActionType.SCROLL_UP)
        if idx == 3:
            return Action(ActionType.SCROLL_DOWN)
        if idx == 4:
            return Action(ActionType.MOUSE_BUTTON_X1)
        if idx == 5:
            return Action(ActionType.MOUSE_BUTTON_X2)
        return Action(ActionType.NONE)
