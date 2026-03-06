from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from synapse_like.remap.actions import (
    ACTION_STRATEGY_MAP,
    Action,
    ActionStrategy,
    ActionType,
    KeystrokeActionStrategy,
    LaunchAppActionStrategy,
    MacroActionStrategy,
    NoneActionStrategy,
    ScrollDownActionStrategy,
    ScrollUpActionStrategy,
)


class ActionDialog(QDialog):
    def __init__(self, key_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurar Ação: {key_label}")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tipo de ação"))

        self.action_type_combo = QComboBox()
        for type_name in ACTION_STRATEGY_MAP:
            self.action_type_combo.addItem(type_name.replace("_", " ").title(), type_name)
        self.action_type_combo.currentIndexChanged.connect(self._update_form)
        layout.addWidget(self.action_type_combo)

        self.forms = QStackedWidget()
        self.forms.addWidget(self._build_none_form())
        self.forms.addWidget(self._build_keystroke_form())
        self.forms.addWidget(self._build_scroll_form("Scroll para cima"))
        self.forms.addWidget(self._build_scroll_form("Scroll para baixo"))
        self.forms.addWidget(self._build_macro_form())
        self.forms.addWidget(self._build_launch_form())
        layout.addWidget(self.forms)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_form()

    def get_action(self) -> Action:
        selected_type = self.action_type_combo.currentData()
        strategy: ActionStrategy
        if selected_type == ActionType.KEYSTROKE.value:
            modifiers = [value.strip() for value in self.modifiers_input.text().split(",") if value.strip()]
            strategy = KeystrokeActionStrategy(
                key=self.key_input.text().strip() or None,
                modifiers=modifiers,
            )
        elif selected_type == ActionType.SCROLL_UP.value:
            strategy = ScrollUpActionStrategy()
        elif selected_type == ActionType.SCROLL_DOWN.value:
            strategy = ScrollDownActionStrategy()
        elif selected_type == ActionType.MACRO.value:
            strategy = MacroActionStrategy()
        elif selected_type == ActionType.LAUNCH_APP.value:
            strategy = LaunchAppActionStrategy(command=self.launch_command_input.text().strip())
        else:
            strategy = NoneActionStrategy()
        return Action(strategy=strategy)

    def set_action(self, action: Action) -> None:
        index = self.action_type_combo.findData(action.type_name)
        if index >= 0:
            self.action_type_combo.setCurrentIndex(index)

        if isinstance(action.strategy, KeystrokeActionStrategy):
            self.key_input.setText(action.strategy.key or "")
            self.modifiers_input.setText(",".join(action.strategy.modifiers))
        elif isinstance(action.strategy, LaunchAppActionStrategy):
            self.launch_command_input.setText(action.strategy.command)

        self._update_form()

    def _update_form(self) -> None:
        selected_type = self.action_type_combo.currentData()
        index_map = {
            ActionType.NONE.value: 0,
            ActionType.KEYSTROKE.value: 1,
            ActionType.SCROLL_UP.value: 2,
            ActionType.SCROLL_DOWN.value: 3,
            ActionType.MACRO.value: 4,
            ActionType.LAUNCH_APP.value: 5,
        }
        self.forms.setCurrentIndex(index_map.get(selected_type, 0))

    def _build_none_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Pass-through. Nenhuma ação customizada será aplicada."))
        return widget

    def _build_keystroke_form(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        self.key_input = QLineEdit()
        self.modifiers_input = QLineEdit()
        self.modifiers_input.setPlaceholderText("KEY_LEFTCTRL, KEY_LEFTSHIFT")
        layout.addRow("Tecla", self.key_input)
        layout.addRow("Modificadores", self.modifiers_input)
        return widget

    def _build_scroll_form(self, label: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(label))
        return widget

    def _build_macro_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("A macro será vinculada à timeline atual da aba MACROS."))
        return widget

    def _build_launch_form(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        self.launch_command_input = QLineEdit()
        self.launch_command_input.setPlaceholderText("Ex: flatpak run org.gimp.GIMP")
        layout.addRow("Comando", self.launch_command_input)
        return widget
