from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MacroTimelineList(QListWidget):
    order_changed = Signal()

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.order_changed.emit()


class MacroEditorWidget(QWidget):
    request_record_start = Signal()
    request_record_stop = Signal()
    macro_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: List[Dict[str, Any]] = []
        self.recording = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        timeline_frame = QFrame()
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.addWidget(QLabel("TIMELINE"))
        self.event_list = MacroTimelineList()
        self.event_list.setDragDropMode(QListWidget.InternalMove)
        self.event_list.currentItemChanged.connect(self._sync_editor_from_selection)
        self.event_list.order_changed.connect(self._sync_events_from_items)
        timeline_layout.addWidget(self.event_list)
        layout.addWidget(timeline_frame, 2)

        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setAlignment(Qt.AlignTop)
        controls_layout.addWidget(QLabel("CONTROLES"))

        self.record_btn = QPushButton("GRAVAR")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self._toggle_record)
        self.record_btn.setProperty("class", "dangerBtn")
        controls_layout.addWidget(self.record_btn)

        add_delay_row = QHBoxLayout()
        self.new_delay_spin = QSpinBox()
        self.new_delay_spin.setRange(1, 10000)
        self.new_delay_spin.setValue(50)
        self.new_delay_spin.setSuffix(" ms")
        add_delay_row.addWidget(self.new_delay_spin)
        add_delay_btn = QPushButton("Adicionar Delay")
        add_delay_btn.clicked.connect(self._add_manual_delay)
        add_delay_row.addWidget(add_delay_btn)
        controls_layout.addLayout(add_delay_row)

        editor_title = QLabel("EDICAO")
        controls_layout.addWidget(editor_title)
        editor_form = QFormLayout()
        self.selected_delay_spin = QSpinBox()
        self.selected_delay_spin.setRange(1, 10000)
        self.selected_delay_spin.setSuffix(" ms")
        self.selected_delay_spin.valueChanged.connect(self._update_selected_delay)
        editor_form.addRow("Delay", self.selected_delay_spin)
        controls_layout.addLayout(editor_form)

        remove_btn = QPushButton("Remover Selecionado")
        remove_btn.clicked.connect(self._remove_selected)
        controls_layout.addWidget(remove_btn)

        clear_btn = QPushButton("Limpar Macro")
        clear_btn.clicked.connect(self.clear_events)
        controls_layout.addWidget(clear_btn)
        controls_layout.addStretch(1)
        layout.addWidget(controls_frame, 1)

        self._sync_editor_state(None)

    def _toggle_record(self) -> None:
        if self.record_btn.isChecked():
            self.recording = True
            self.record_btn.setText("PARAR")
            self.request_record_start.emit()
            return
        self.stop_recording_ui()
        self.request_record_stop.emit()

    def stop_recording_ui(self) -> None:
        self.recording = False
        self.record_btn.setChecked(False)
        self.record_btn.setText("GRAVAR")

    def set_events(self, events: List[Dict[str, Any]]) -> None:
        self.events = [dict(event) for event in events]
        self.event_list.clear()
        for event in self.events:
            self._append_item(event)
        self.macro_updated.emit(self.events)

    def add_event(self, event: Dict[str, Any]) -> None:
        self.events.append(dict(event))
        self._append_item(event)
        self.macro_updated.emit(self.events)

    def clear_events(self) -> None:
        self.events.clear()
        self.event_list.clear()
        self.macro_updated.emit(self.events)
        self._sync_editor_state(None)

    def _append_item(self, event: Dict[str, Any]) -> None:
        item = QListWidgetItem(self._event_label(event))
        item.setData(Qt.UserRole, dict(event))
        self.event_list.addItem(item)
        self.event_list.scrollToBottom()

    def _event_label(self, event: Dict[str, Any]) -> str:
        if event.get("type") == "delay":
            return f"Delay {int(event.get('value', 0))} ms"
        state = "DOWN" if int(event.get("state", 1)) == 1 else "UP"
        return f"{event.get('code', 'KEY_UNKNOWN')} {state}"

    def _add_manual_delay(self) -> None:
        self.add_event({"type": "delay", "value": self.new_delay_spin.value()})

    def _remove_selected(self) -> None:
        row = self.event_list.currentRow()
        if row < 0:
            return
        self.event_list.takeItem(row)
        if row < len(self.events):
            self.events.pop(row)
        self.macro_updated.emit(self.events)
        self._sync_editor_state(self.event_list.currentItem())

    def _sync_events_from_items(self) -> None:
        self.events = []
        for index in range(self.event_list.count()):
            item = self.event_list.item(index)
            payload = item.data(Qt.UserRole)
            if isinstance(payload, dict):
                self.events.append(dict(payload))
        self.macro_updated.emit(self.events)

    def _sync_editor_from_selection(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        self._sync_editor_state(current)

    def _sync_editor_state(self, item: QListWidgetItem | None) -> None:
        is_delay = bool(item and isinstance(item.data(Qt.UserRole), dict) and item.data(Qt.UserRole).get("type") == "delay")
        self.selected_delay_spin.blockSignals(True)
        if is_delay:
            self.selected_delay_spin.setValue(int(item.data(Qt.UserRole).get("value", 1)))
        else:
            self.selected_delay_spin.setValue(1)
        self.selected_delay_spin.blockSignals(False)
        self.selected_delay_spin.setEnabled(is_delay)

    def _update_selected_delay(self, value: int) -> None:
        item = self.event_list.currentItem()
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not isinstance(payload, dict) or payload.get("type") != "delay":
            return
        payload = dict(payload)
        payload["value"] = value
        item.setData(Qt.UserRole, payload)
        item.setText(self._event_label(payload))
        self._sync_events_from_items()
