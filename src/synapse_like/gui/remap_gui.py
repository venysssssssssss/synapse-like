from __future__ import annotations

import logging
import queue
import select
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from evdev import InputDevice, ecodes
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from synapse_like.adapters.openrazer import OpenRazerAdapter
from synapse_like.gui.constants import KEY_ALIASES, KEYMAP, MOUSE_ALIASES, MOUSEMAP
from synapse_like.gui.device_manager import DeviceInfo, DeviceManager
from synapse_like.gui.dialogs import ActionDialog
from synapse_like.gui.icons import build_app_icon
from synapse_like.gui.profile_service import ProfileService, ProfileSummary
from synapse_like.gui.remap_service import RemapService
from synapse_like.gui.theme import STYLE_SHEET
from synapse_like.gui.utils import event_code_name
from synapse_like.gui.widgets.keyboard_svg import KeyboardSvgWidget
from synapse_like.gui.widgets.macro_editor import MacroEditorWidget
from synapse_like.gui.widgets.mouse_svg import MouseSvgWidget
from synapse_like.remap.actions import Action, ActionType
from synapse_like.remap.device_paths import expand_related_paths
from synapse_like.remap.window_monitor import WindowMonitor

logger = logging.getLogger(__name__)

KEY_LABEL_BY_CODE = {code: label for label, code in KEYMAP.items()}


class GuiSignals(QObject):
    window_changed = Signal(str)
    devices_changed = Signal(list)


class RemapGUI(QMainWindow):
    def __init__(self, app_icon=None):
        super().__init__()
        self.setWindowTitle("Synapse-Like")
        self.setWindowIcon(app_icon or build_app_icon())
        self.resize(1380, 900)

        self.device_manager = DeviceManager()
        self.profile_service = ProfileService()
        self.remap_service = RemapService()
        self.window_monitor = WindowMonitor()
        self.hardware_adapter = OpenRazerAdapter()
        self.gui_signals = GuiSignals()

        self.mappings: Dict[str, Action] = {
            "KEY_F13": Action(ActionType.SCROLL_UP),
            "KEY_F14": Action(ActionType.SCROLL_DOWN),
        }
        self.dynamic_aliases: Dict[str, List[str]] = {}
        self.key_id_map: Dict[str, Dict[str, str]] = {}
        self.linked_apps: List[str] = []
        self.current_profile: Optional[ProfileSummary] = None

        self.capture_active = False
        self.capture_mode = ""
        self.capture_sequence: List[str] = []
        self.capture_index = 0
        self.capture_paths: List[str] = []
        self.capture_thread: Optional[threading.Thread] = None
        self.capture_queue: queue.Queue[tuple] = queue.Queue()
        self.capture_stop = threading.Event()
        self._last_macro_timestamp: Optional[float] = None
        self._quit_requested = False

        self.service_timer = QTimer(self)
        self.service_timer.setInterval(40)
        self.service_timer.timeout.connect(self._poll_service_queue)

        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(40)
        self.capture_timer.timeout.connect(self._poll_capture_queue)

        self.feedback_timer = QTimer(self)
        self.feedback_timer.setInterval(60)
        self.feedback_timer.timeout.connect(self._poll_feedback)

        self.gui_signals.window_changed.connect(self._handle_window_changed)
        self.gui_signals.devices_changed.connect(self._handle_devices_changed)

        self._build_ui()
        self._init_tray()
        self._apply_theme()
        self._refresh_profiles()
        self._populate_devices(self.device_manager.scan())
        self._sync_visual_state()

        self.device_manager.subscribe(self.gui_signals.devices_changed.emit)
        self.device_manager.start_monitoring()
        self.window_monitor.start(self.gui_signals.window_changed.emit)
        self.service_timer.start()
        self.capture_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_tabs(), 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_device_dock())

        self.status_label = QLabel("Pronto.")
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setMinimumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setSpacing(14)

        layout.addWidget(self._build_profile_card())
        layout.addWidget(self._build_device_card())
        layout.addWidget(self._build_action_card())
        layout.addStretch(1)
        return panel

    def _build_profile_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.addWidget(self._card_title("PERFIS"))

        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_combo)

        form = QFormLayout()
        self.profile_name_input = QLineEdit("Default")
        self.linked_app_input = QLineEdit()
        self.linked_app_input.setPlaceholderText("Ex: firefox, gimp")
        self.linked_app_input.textChanged.connect(self._update_linked_apps)
        form.addRow("Nome", self.profile_name_input)
        form.addRow("Auto-Switch", self.linked_app_input)
        layout.addLayout(form)

        button_grid = QGridLayout()
        self.new_profile_btn = QPushButton("Novo")
        self.load_profile_btn = QPushButton("Carregar")
        self.save_profile_btn = QPushButton("Salvar")
        self.delete_profile_btn = QPushButton("Excluir")
        self.new_profile_btn.clicked.connect(self._new_profile)
        self.load_profile_btn.clicked.connect(self._load_selected_profile)
        self.save_profile_btn.clicked.connect(self._save_current_profile)
        self.delete_profile_btn.clicked.connect(self._delete_selected_profile)
        for button in (
            self.new_profile_btn,
            self.load_profile_btn,
            self.save_profile_btn,
            self.delete_profile_btn,
        ):
            button.setProperty("class", "secondaryBtn")
        button_grid.addWidget(self.new_profile_btn, 0, 0)
        button_grid.addWidget(self.load_profile_btn, 0, 1)
        button_grid.addWidget(self.save_profile_btn, 1, 0)
        button_grid.addWidget(self.delete_profile_btn, 1, 1)
        layout.addLayout(button_grid)
        return card

    def _build_device_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.addWidget(self._card_title("DISPOSITIVO"))

        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        layout.addWidget(self.device_combo)

        self.learn_mx_btn = QPushButton("Aprender M-Keys")
        self.learn_all_btn = QPushButton("Aprender Teclado")
        self.learn_mx_btn.clicked.connect(self._toggle_mx_capture)
        self.learn_all_btn.clicked.connect(self._toggle_full_capture)
        self.learn_mx_btn.setProperty("class", "secondaryBtn")
        self.learn_all_btn.setProperty("class", "secondaryBtn")
        layout.addWidget(self.learn_mx_btn)
        layout.addWidget(self.learn_all_btn)
        return card

    def _build_action_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.addWidget(self._card_title("SERVICO"))

        self.apply_btn = QPushButton("Aplicar Remap")
        self.apply_btn.setProperty("class", "primaryBtn")
        self.stop_btn = QPushButton("Parar Remap")
        self.stop_btn.setProperty("class", "dangerBtn")
        self.persist_btn = QPushButton("Salvar na Memoria do Dispositivo")
        self.persist_btn.setProperty("class", "secondaryBtn")
        self.apply_btn.clicked.connect(self._apply)
        self.stop_btn.clicked.connect(self._stop)
        self.persist_btn.clicked.connect(self._persist_to_device)

        layout.addWidget(self.apply_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.persist_btn)
        return card

    def _build_tabs(self) -> QWidget:
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._build_keyboard_tab(), "Teclado")
        self.tab_widget.addTab(self._build_mouse_tab(), "Mouse")
        self.tab_widget.addTab(self._build_macros_tab(), "Macros")
        return self.tab_widget

    def _build_keyboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._section_title("MAPEAMENTO VISUAL"))
        self.keyboard_svg = KeyboardSvgWidget()
        self.keyboard_svg.clicked.connect(self._choose_keyboard_action)
        layout.addWidget(self.keyboard_svg, 1)
        return page

    def _build_mouse_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._section_title("MOUSE"))
        self.mouse_svg = MouseSvgWidget()
        self.mouse_svg.clicked.connect(self._choose_mouse_action)
        layout.addWidget(self.mouse_svg, 1)
        return page

    def _build_macros_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._section_title("EDITOR DE MACROS"))
        self.macro_editor = MacroEditorWidget()
        self.macro_editor.request_record_start.connect(self._start_macro_record)
        self.macro_editor.request_record_stop.connect(self._stop_macro_record)
        layout.addWidget(self.macro_editor, 1)
        return page

    def _build_device_dock(self) -> QWidget:
        dock = QFrame()
        dock.setObjectName("deviceDock")
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self._section_title("DISPOSITIVOS DETECTADOS"))
        self.device_cards_layout = QHBoxLayout()
        self.device_cards_layout.setSpacing(8)
        layout.addLayout(self.device_cards_layout, 1)
        return dock

    def _card_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("class", "cardTitle")
        return label

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("pageTitle")
        return label

    def _apply_theme(self) -> None:
        self.setStyleSheet(STYLE_SHEET)

    def _init_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(build_app_icon(), self)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_menu = QMenu(self)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        self._rebuild_tray_menu()

    def _rebuild_tray_menu(self) -> None:
        self.tray_menu.clear()
        open_action = QAction("Mostrar Janela", self)
        open_action.triggered.connect(self._restore_from_tray)
        self.tray_menu.addAction(open_action)

        toggle_action = QAction("Parar Remap" if self.remap_service.is_active() else "Aplicar Remap", self)
        toggle_action.triggered.connect(self._stop if self.remap_service.is_active() else self._apply)
        self.tray_menu.addAction(toggle_action)
        self.tray_menu.addSeparator()

        profiles_menu = self.tray_menu.addMenu("Perfis")
        for profile in self.profile_service.list_profiles():
            action = profiles_menu.addAction(profile.name)
            action.triggered.connect(
                lambda checked=False, profile_name=profile.name: self._load_named_profile(profile_name, apply_after_load=True)
            )

        self.tray_menu.addSeparator()
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self._quit_from_tray)
        self.tray_menu.addAction(quit_action)

    def _refresh_profiles(self) -> None:
        profiles = self.profile_service.list_profiles()
        current_name = self.current_profile.name if self.current_profile else self.profile_combo.currentText()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems([profile.name for profile in profiles])
        self.profile_combo.blockSignals(False)
        if profiles:
            if current_name and current_name in [profile.name for profile in profiles]:
                self.profile_combo.setCurrentText(current_name)
            else:
                self.profile_combo.setCurrentIndex(0)
        self._rebuild_tray_menu()

    def _populate_devices(self, devices: Iterable[DeviceInfo]) -> None:
        current_path = self.device_combo.currentText().strip()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        device_list = list(devices)
        for device in device_list:
            self.device_combo.addItem(device.path)
        self.device_combo.blockSignals(False)

        if current_path:
            self.device_combo.setCurrentText(current_path)
        elif device_list:
            self.device_combo.setCurrentText(device_list[0].path)

        while self.device_cards_layout.count():
            item = self.device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for device in self.device_manager.get_primary_devices():
            card = QFrame()
            card.setObjectName("deviceCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.addWidget(QLabel(device.name))
            layout.addWidget(QLabel(device.kind.title()))
            self.device_cards_layout.addWidget(card)

    def _sync_visual_state(self) -> None:
        keyboard_codes: set[str] = set()
        mouse_labels: set[str] = set()
        keyboard_tooltips: dict[str, str] = {}
        mouse_tooltips: dict[str, str] = {}

        for label, fallback in KEYMAP.items():
            action = self._action_for_label(label, fallback)
            if not action or action.type == ActionType.NONE:
                continue
            keyboard_codes.add(fallback)
            keyboard_tooltips[fallback] = f"{label}: {self._action_text(action)}"

        for label, fallback in MOUSEMAP.items():
            action = self._action_for_label(label, fallback)
            if not action or action.type == ActionType.NONE:
                continue
            mouse_labels.add(label)
            mouse_tooltips[label] = f"{label}: {self._action_text(action)}"

        self.keyboard_svg.set_mapped_keys(keyboard_codes)
        self.keyboard_svg.set_tooltip_map(keyboard_tooltips)
        self.mouse_svg.set_mapped_buttons(mouse_labels)
        self.mouse_svg.set_tooltip_map(mouse_tooltips)

    def _choose_keyboard_action(self, key_code: str) -> None:
        label = KEY_LABEL_BY_CODE.get(key_code, key_code)
        self._choose_action(label, key_code)

    def _choose_mouse_action(self, label: str) -> None:
        self._choose_action(label, MOUSEMAP[label])

    def _choose_action(self, label: str, fallback_code: str) -> None:
        dialog = ActionDialog(label, self)
        current_action = self._action_for_label(label, fallback_code)
        if current_action:
            dialog.set_action(current_action)
        if dialog.exec() != dialog.Accepted:
            return

        action = dialog.get_action()
        if action.type == ActionType.MACRO:
            action = Action(ActionType.MACRO, {"events": self.macro_editor.events})

        codes = self._codes_for_label(label, fallback_code)
        if action.type == ActionType.NONE:
            for code in codes:
                self.mappings.pop(code, None)
        else:
            for code in codes:
                self.mappings[code] = action

        self._sync_visual_state()
        self._set_status(f"{label} -> {self._action_text(action)}")

    def _action_for_label(self, label: str, fallback_code: str) -> Optional[Action]:
        for code in self._codes_for_label(label, fallback_code):
            action = self.mappings.get(code)
            if action is not None:
                return action
        return None

    def _codes_for_label(self, label: str, fallback_code: str) -> list[str]:
        if label in self.dynamic_aliases:
            return self.dynamic_aliases[label]
        if label in KEY_ALIASES:
            return KEY_ALIASES[label]
        if label in MOUSE_ALIASES:
            return MOUSE_ALIASES[label]
        return [fallback_code]

    def _save_current_profile(self) -> None:
        profile_name = self.profile_name_input.text().strip() or "Default"
        path = self.profile_service.save_named_profile(
            name=profile_name,
            device_path=self.device_combo.currentText().strip(),
            mappings=self.mappings,
            dynamic_aliases=self.dynamic_aliases,
            key_id_map=self.key_id_map,
            linked_apps=self.linked_apps,
        )
        self.current_profile = ProfileSummary(
            name=profile_name,
            path=path,
            linked_apps=[app.casefold() for app in self.linked_apps],
            device_path=self.device_combo.currentText().strip(),
        )
        self._refresh_profiles()
        self.profile_combo.setCurrentText(profile_name)
        self._set_status(f"Perfil salvo em {path}")

    def _load_selected_profile(self) -> None:
        profile_name = self.profile_combo.currentText().strip()
        if not profile_name:
            QMessageBox.information(self, "Perfis", "Nenhum perfil salvo ainda.")
            return
        self._load_named_profile(profile_name)

    def _load_named_profile(self, profile_name: str, apply_after_load: bool = False) -> None:
        try:
            device_path, mappings, dynamic_aliases, key_id_map, linked_apps = self.profile_service.load_named_profile(profile_name)
        except Exception as exc:
            QMessageBox.critical(self, "Perfil", f"Nao foi possivel carregar o perfil: {exc}")
            return

        self.mappings = mappings
        self.dynamic_aliases = dynamic_aliases
        self.key_id_map = key_id_map
        self.linked_apps = linked_apps
        self.profile_name_input.setText(profile_name)
        self.linked_app_input.setText(", ".join(linked_apps))
        if device_path:
            self.device_combo.setCurrentText(device_path)
        self.current_profile = ProfileSummary(
            name=profile_name,
            path=self.profile_service.get_profile_path(profile_name),
            linked_apps=[app.casefold() for app in linked_apps],
            device_path=device_path,
        )
        self._sync_visual_state()
        self._set_status(f"Perfil '{profile_name}' carregado.")
        if apply_after_load and self.device_combo.currentText().strip():
            self._apply()

    def _delete_selected_profile(self) -> None:
        profile_name = self.profile_combo.currentText().strip()
        if not profile_name:
            return
        if not self.profile_service.delete_profile(profile_name):
            return
        if self.current_profile and self.current_profile.name == profile_name:
            self.current_profile = None
        self._refresh_profiles()
        self._set_status(f"Perfil '{profile_name}' removido.")

    def _new_profile(self) -> None:
        self.current_profile = None
        self.profile_name_input.setText("Novo Perfil")
        self.linked_app_input.clear()
        self.mappings = {
            "KEY_F13": Action(ActionType.SCROLL_UP),
            "KEY_F14": Action(ActionType.SCROLL_DOWN),
        }
        self.dynamic_aliases = {}
        self.key_id_map = {}
        self.linked_apps = []
        self.macro_editor.clear_events()
        self._sync_visual_state()
        self._set_status("Perfil limpo.")

    def _on_profile_selected(self, profile_name: str) -> None:
        if profile_name:
            self.profile_name_input.setText(profile_name)

    def _toggle_mx_capture(self) -> None:
        if self.capture_active:
            self._stop_capture("Escuta cancelada.")
            return
        self._start_capture(["M5", "M4", "M3", "M2", "M1"], mode="learn")

    def _toggle_full_capture(self) -> None:
        if self.capture_active:
            self._stop_capture("Escuta cancelada.")
            return
        sequence = [label for label in KEYMAP if label in KEYMAP]
        self._start_capture(sequence, mode="learn")

    def _start_macro_record(self) -> None:
        self._start_capture([], mode="macro")
        self._set_status("Gravando macro...")

    def _stop_macro_record(self) -> None:
        self._stop_capture("Gravacao de macro finalizada.")

    def _start_capture(self, sequence: list[str], mode: str) -> None:
        device = self.device_combo.currentText().strip()
        if not device:
            QMessageBox.warning(self, "Device", "Selecione um device antes de iniciar a escuta.")
            return

        paths = expand_related_paths(device)
        if not paths:
            QMessageBox.warning(self, "Device", "Nenhuma interface de evento foi encontrada.")
            return

        self.capture_mode = mode
        self.capture_sequence = sequence
        self.capture_index = 0
        self.capture_paths = paths
        self.capture_active = True
        self.capture_stop.clear()
        self._last_macro_timestamp = None

        self.learn_mx_btn.setText("Parar Escuta")
        self.learn_all_btn.setText("Parar Escuta")
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        if mode == "learn":
            self._show_capture_prompt()

    def _stop_capture(self, message: str = "") -> None:
        self.capture_stop.set()
        self.capture_active = False
        self.capture_mode = ""
        self.capture_sequence = []
        self.capture_paths = []
        self.learn_mx_btn.setText("Aprender M-Keys")
        self.learn_all_btn.setText("Aprender Teclado")
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=0.4)
        self.capture_thread = None
        self.macro_editor.stop_recording_ui()
        if message:
            self._set_status(message)

    def _capture_loop(self) -> None:
        devices: list[InputDevice] = []
        failures: list[str] = []
        try:
            for path in self.capture_paths:
                try:
                    devices.append(InputDevice(path))
                except Exception as exc:
                    failures.append(f"{path}: {exc}")

            if not devices:
                self.capture_queue.put(("error", "Falha abrindo devices", failures))
                return
            if failures:
                self.capture_queue.put(("warn", "\n".join(failures)))

            while not self.capture_stop.is_set():
                readable, _, _ = select.select(devices, [], [], 0.2)
                for device in readable:
                    for event in device.read():
                        if event.type != ecodes.EV_KEY or event.value == 2:
                            continue
                        if self.capture_mode != "macro" and event.value != 1:
                            continue
                        self.capture_queue.put(
                            (
                                "hit",
                                event_code_name(event.code),
                                str(event.code),
                                device.path,
                                event.value,
                                time.monotonic(),
                            )
                        )
        finally:
            for device in devices:
                try:
                    device.close()
                except Exception:
                    pass

    def _poll_capture_queue(self) -> None:
        while True:
            try:
                item = self.capture_queue.get_nowait()
            except queue.Empty:
                return

            kind = item[0]
            if kind == "error":
                self._stop_capture("Falha na escuta.")
                failures = "\n".join(item[2]) if len(item) > 2 else ""
                QMessageBox.critical(self, "Escuta", f"{item[1]}\n{failures}")
                continue
            if kind == "warn":
                self._set_status(str(item[1]))
                continue

            _, code_name, code_num, path, event_value, timestamp = item
            if self.capture_mode == "macro":
                if self._last_macro_timestamp is not None:
                    delay_ms = int((timestamp - self._last_macro_timestamp) * 1000)
                    if delay_ms > 0:
                        self.macro_editor.add_event({"type": "delay", "value": delay_ms})
                self._last_macro_timestamp = timestamp
                self.macro_editor.add_event({"type": "key", "code": code_name, "state": event_value})
                continue

            if not self.capture_active or self.capture_index >= len(self.capture_sequence):
                continue

            target_label = self.capture_sequence[self.capture_index]
            self._register_learned_id(target_label, code_name, code_num, path)
            self.capture_index += 1
            self._show_capture_prompt()

    def _show_capture_prompt(self) -> None:
        if self.capture_index >= len(self.capture_sequence):
            self._stop_capture("Escuta finalizada.")
            return
        target = self.capture_sequence[self.capture_index]
        self._set_status(f"Pressione {target} para aprender o ID.")

    def _register_learned_id(self, label: str, code_name: str, code_num: str, path: str) -> None:
        aliases = [code_name, code_num]
        for value in self.dynamic_aliases.get(label, []):
            if value not in aliases:
                aliases.append(value)
        self.dynamic_aliases[label] = aliases
        self.key_id_map[label] = {
            "symbolic": code_name,
            "numeric": code_num,
            "path": path,
        }
        self._sync_visual_state()

    def _update_linked_apps(self, text: str) -> None:
        self.linked_apps = [app.strip().casefold() for app in text.split(",") if app.strip()]

    def _apply(self) -> None:
        if self.remap_service.is_busy():
            self._set_status("Aguardando operação atual terminar.")
            return
        device = self.device_combo.currentText().strip()
        if not device:
            QMessageBox.warning(self, "Device", "Selecione um device antes de aplicar.")
            return
        self._stop_capture()
        self._set_service_busy(True, "Aplicando remap...")
        self.remap_service.apply_configuration(device, self.mappings)

    def _stop(self) -> None:
        if self.remap_service.is_busy():
            self._set_status("Aguardando operação atual terminar.")
            return
        if not self.remap_service.is_active():
            self._set_status("Remap já está parado.")
            return
        self._set_service_busy(True, "Parando remap...")
        self.remap_service.stop_all()

    def _set_service_busy(self, busy: bool, status: str | None = None) -> None:
        for widget in (
            self.apply_btn,
            self.stop_btn,
            self.persist_btn,
            self.save_profile_btn,
            self.load_profile_btn,
            self.new_profile_btn,
            self.delete_profile_btn,
            self.learn_mx_btn,
            self.learn_all_btn,
            self.device_combo,
        ):
            widget.setEnabled(not busy)
        if status:
            self._set_status(status)

    def _poll_service_queue(self) -> None:
        while True:
            try:
                message = self.remap_service.service_queue.get_nowait()
            except queue.Empty:
                return

            kind = message.get("kind")
            if kind == "apply_done":
                self._handle_apply_done(message)
            elif kind == "stop_done":
                self._handle_stop_done(message)

    def _handle_apply_done(self, message: Dict[str, Any]) -> None:
        self._set_service_busy(False)
        failures = message.get("failures", [])
        active_count = int(message.get("active_count", 0))
        if active_count == 0:
            QMessageBox.critical(self, "Remap", "\n".join(failures or ["Falha ao iniciar mapper."]))
            self._set_status("Remap parado.")
            return
        if failures:
            QMessageBox.warning(self, "Remap", "Interfaces com falha:\n" + "\n".join(failures))
        suffix = " (baixa latência)" if message.get("low_latency") else ""
        self._set_status(f"Remap ativo em {active_count} interface(s){suffix}.")
        self.feedback_timer.start()
        self._rebuild_tray_menu()

    def _handle_stop_done(self, message: Dict[str, Any]) -> None:
        self._set_service_busy(False)
        failures = message.get("failures", [])
        if failures:
            QMessageBox.warning(self, "Remap", "Falhas ao parar:\n" + "\n".join(failures))
        self.feedback_timer.stop()
        self._set_status("Remap parado.")
        self._rebuild_tray_menu()

    def _poll_feedback(self) -> None:
        if not self.remap_service.is_active():
            return
        active_keys = self.remap_service.get_input_state()
        self.keyboard_svg.set_active_keys(active_keys)
        self.mouse_svg.set_active_keys(active_keys)

    def _persist_to_device(self) -> None:
        profile_name = self.profile_name_input.text().strip() or "Default"
        payload = {
            "device_path": self.device_combo.currentText().strip(),
            "mappings": {key: action.to_dict() for key, action in self.mappings.items()},
            "linked_apps": list(self.linked_apps),
        }
        result = self.hardware_adapter.persist_profile(profile_name, payload)
        QMessageBox.information(self, "Persistência Onboard", result)
        self._set_status(result)

    def _handle_window_changed(self, wm_class: str) -> None:
        profile = self.profile_service.find_profile_for_window_class(wm_class)
        if profile is None:
            return
        if self.current_profile and profile.name == self.current_profile.name:
            return
        self._load_named_profile(profile.name, apply_after_load=self.remap_service.is_active())
        self._set_status(f"Auto-switch: perfil '{profile.name}' ativado para {wm_class}.")

    def _handle_devices_changed(self, devices: list[DeviceInfo]) -> None:
        self._populate_devices(devices)
        self._set_status("Hotplug detectado. Lista de devices atualizada.")

    def _action_text(self, action: Action) -> str:
        if action.type == ActionType.KEYSTROKE:
            return f"Keystroke {action.strategy.key or ''}".strip()
        if action.type == ActionType.MACRO:
            event_count = len(getattr(action.strategy, "events", []))
            return f"Macro ({event_count} eventos)"
        if action.type == ActionType.LAUNCH_APP:
            return f"Lançar app: {action.strategy.command}"
        return action.type.value.replace("_", " ").title()

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._quit_requested = True
        self.close()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._restore_from_tray()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._quit_requested and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Synapse-Like",
                "A aplicação continua rodando na bandeja do sistema.",
                QSystemTrayIcon.Information,
                2500,
            )
            return

        self.window_monitor.stop()
        self.device_manager.stop_monitoring()
        self._stop_capture()
        if self.remap_service.is_active():
            self.remap_service.stop_all()
            if self.remap_service._thread and self.remap_service._thread.is_alive():
                self.remap_service._thread.join(timeout=0.5)
        self.tray_icon.hide()
        super().closeEvent(event)


def launch() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    app = QApplication.instance() or QApplication([])
    icon = build_app_icon()
    app.setWindowIcon(icon)
    app.setApplicationName("synapse-like")
    app.setApplicationDisplayName("Synapse-Like")
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("synapse-like")
    window = RemapGUI(app_icon=icon)
    window.show()
    app.exec()


if __name__ == "__main__":
    launch()
