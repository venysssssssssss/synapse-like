import logging
import os
import queue
import select
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from evdev import InputDevice, ecodes
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from synapse_like.gui.constants import (
    FULL_KEY_CAPTURE_SEQUENCE,
    KEY_ALIASES,
    KEYBOARD_LAYOUT,
    KEYMAP,
    MOUSE_ALIASES,
    MOUSEMAP,
    MX_CAPTURE_SEQUENCE,
    SUB_TAB_ORDER,
    TOP_TAB_ORDER,
)
from synapse_like.gui.device_paths import card_name, detect_razer_devices, expand_related_paths, path_kind
from synapse_like.gui.dialogs import ActionDialog
from synapse_like.gui.mapping_io import load_mapping_file, save_mapping_file
from synapse_like.gui.theme import STYLE_SHEET
from synapse_like.gui.utils import event_code_name
from synapse_like.remap.actions import Action, ActionType
from synapse_like.remap.mapper import InputMapper, MappingConfig
from synapse_like.remap.strategy import extract_mapped_codes, is_aux_pointer_only_mapping

logger = logging.getLogger(__name__)


class RemapGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Synapse-Like")
        self.resize(1400, 860)

        # Default mappings for BlackWidow Ultimate 2013 (M1=F13, M2=F14).
        self.mappings: Dict[str, Action] = {
            "KEY_F13": Action(ActionType.SCROLL_UP),
            "KEY_F14": Action(ActionType.SCROLL_DOWN),
        }
        self.label_actions: Dict[str, Action] = {}
        self.dynamic_aliases: Dict[str, List[str]] = {}
        self.key_id_map: Dict[str, Dict[str, str]] = {}
        self.mappers: List[InputMapper] = []
        self.detected_devices = detect_razer_devices()

        self.keyboard_buttons: Dict[str, QPushButton] = {}
        self.mouse_buttons: Dict[str, QPushButton] = {}
        self.top_tabs: Dict[str, QPushButton] = {}
        self.sub_tabs: Dict[str, QPushButton] = {}
        self.current_top_tab = "TECLADO"

        self.capture_thread: threading.Thread | None = None
        self.capture_queue: queue.Queue[Tuple[str, str, str, str] | Tuple[str, str]] = queue.Queue()
        self.capture_stop = threading.Event()
        self.capture_active = False
        self.capture_mode = ""
        self.capture_sequence: List[str] = []
        self.capture_idx = 0
        self.capture_paths: List[str] = []

        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(100)
        self.capture_timer.timeout.connect(self._poll_capture_queue)
        self.capture_timer.start()

        self._build_ui()
        self._apply_theme()
        self._populate_devices()
        self._set_top_tab("TECLADO")

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(8)

        primary_row = QHBoxLayout()
        primary_row.setSpacing(8)
        for tab_name in TOP_TAB_ORDER:
            button = QPushButton(tab_name)
            button.setCheckable(True)
            button.setObjectName("topTab")
            button.clicked.connect(lambda _, name=tab_name: self._set_top_tab(name))
            self.top_tabs[tab_name] = button
            primary_row.addWidget(button)
        primary_row.addSpacerItem(
            QSpacerItem(30, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        logo = QLabel("RAZER")
        logo.setObjectName("brand")
        primary_row.addWidget(logo)
        top_layout.addLayout(primary_row)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        for tab_name in SUB_TAB_ORDER:
            button = QPushButton(tab_name)
            button.setCheckable(True)
            button.setObjectName("subTab")
            button.setChecked(tab_name == "PERSONALIZAR")
            self.sub_tabs[tab_name] = button
            sub_row.addWidget(button)
        sub_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_layout.addLayout(sub_row)
        top_bar.setLayout(top_layout)
        root.addWidget(top_bar)

        body = QFrame()
        body.setObjectName("bodyFrame")
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(14)
        body_layout.addWidget(self._build_left_panel(), 0)

        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(self._build_keyboard_page())
        self.page_stack.addWidget(self._build_mouse_page())
        self.page_stack.addWidget(self._build_macros_page())
        body_layout.addWidget(self.page_stack, 1)

        body.setLayout(body_layout)
        root.addWidget(body, 1)
        root.addWidget(self._build_device_dock())
        self.setLayout(root)

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setMinimumWidth(320)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # --- Profiles Card ---
        profile_card = QFrame()
        profile_card.setProperty("class", "card")
        p_layout = QVBoxLayout()
        p_layout.setContentsMargins(16, 16, 16, 16)
        p_layout.setSpacing(10)
        
        lbl_profile = QLabel("PERFIL")
        lbl_profile.setProperty("class", "cardTitle")
        p_layout.addWidget(lbl_profile)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Default", "Work", "Gaming"])
        p_layout.addWidget(self.profile_combo)

        profile_actions = QHBoxLayout()
        profile_actions.setSpacing(8)
        for text in ["+", "Rename", "Delete"]:
            btn = QPushButton(text)
            btn.setProperty("class", "iconBtn")
            profile_actions.addWidget(btn)
        p_layout.addLayout(profile_actions)

        lbl_name = QLabel("NOME DO PERFIL")
        lbl_name.setProperty("class", "fieldLabel")
        p_layout.addWidget(lbl_name)
        
        self.profile_name = QLineEdit("Default")
        p_layout.addWidget(self.profile_name)

        # Shortcuts section in profile card
        lbl_shortcut = QLabel("ATALHO DE TROCA")
        lbl_shortcut.setProperty("class", "fieldLabel")
        p_layout.addWidget(lbl_shortcut)
        
        self.shortcut_combo = QComboBox()
        self.shortcut_combo.addItems(["FN + 1", "FN + 2", "FN + 3", "None"])
        p_layout.addWidget(self.shortcut_combo)

        self.link_program_cb = QCheckBox("Vincular programa")
        p_layout.addWidget(self.link_program_cb)
        
        profile_card.setLayout(p_layout)
        main_layout.addWidget(profile_card)

        # --- Device / Actions Card ---
        action_card = QFrame()
        action_card.setProperty("class", "card")
        a_layout = QVBoxLayout()
        a_layout.setContentsMargins(16, 16, 16, 16)
        a_layout.setSpacing(10)

        lbl_device = QLabel("DEVICE PATH")
        lbl_device.setProperty("class", "cardTitle")
        a_layout.addWidget(lbl_device)

        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._combo_to_input)
        self.device_input = QLineEdit()
        self.device_input.setPlaceholderText("/dev/input/by-id/...")
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.device_input, 2)
        a_layout.addLayout(device_row)

        a_layout.addSpacing(10)
        lbl_actions = QLabel("ACOES")
        lbl_actions.setProperty("class", "cardTitle")
        a_layout.addWidget(lbl_actions)

        self.learn_mx_btn = QPushButton("Mapear M-X (escutar)")
        self.learn_all_btn = QPushButton("Mapear teclado completo")
        self.save_btn = QPushButton("Salvar Profile")
        self.load_btn = QPushButton("Carregar Profile")
        self.apply_btn = QPushButton("APLICAR NO SYSTEMA")
        self.apply_btn.setProperty("class", "primaryBtn")
        self.stop_btn = QPushButton("Parar Servico")
        self.stop_btn.setProperty("class", "dangerBtn")

        self.learn_mx_btn.clicked.connect(self._toggle_mx_capture)
        self.learn_all_btn.clicked.connect(self._toggle_full_capture)
        self.save_btn.clicked.connect(self._save)
        self.load_btn.clicked.connect(self._load)
        self.apply_btn.clicked.connect(self._apply)
        self.stop_btn.clicked.connect(self._stop)

        for btn in [self.learn_mx_btn, self.learn_all_btn, self.save_btn, self.load_btn]:
            btn.setProperty("class", "secondaryBtn")
            a_layout.addWidget(btn)
        
        a_layout.addSpacing(10)
        a_layout.addWidget(self.apply_btn)
        a_layout.addWidget(self.stop_btn)

        action_card.setLayout(a_layout)
        main_layout.addWidget(action_card)

        # Status at bottom
        self.status_label = QLabel("Pronto.")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("statusLabel")
        main_layout.addWidget(self.status_label)
        
        main_layout.addStretch(1)
        panel.setLayout(main_layout)
        return panel

    def _build_keyboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("TECLADO - PERSONALIZAR"))

        keyboard_frame = QFrame()
        keyboard_frame.setObjectName("keyboardFrame")
        grid = QGridLayout()
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setVerticalSpacing(6)
        grid.setHorizontalSpacing(6)

        for row_index, row in enumerate(KEYBOARD_LAYOUT):
            col = 0
            for key_label, span in row:
                button = QPushButton(key_label)
                button.setObjectName("keyButton")
                button.setProperty("mapped", "false")
                button.setFixedHeight(34)
                if key_label in KEYMAP:
                    button.clicked.connect(
                        lambda _, label=key_label: self._choose_action(label, KEYMAP[label])
                    )
                    self.keyboard_buttons[key_label] = button
                grid.addWidget(button, row_index, col, 1, span)
                col += span

        keyboard_frame.setLayout(grid)
        layout.addWidget(keyboard_frame)
        page.setLayout(layout)
        return page

    def _build_mouse_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        list_panel = QFrame()
        list_panel.setObjectName("mouseListPanel")
        list_layout = QVBoxLayout()
        list_layout.addWidget(self._section_title("MOUSE - PERSONALIZAR"))

        for index, label in [("1", "LMB"), ("2", "MMB"), ("3", "RMB"), ("4", "M4"), ("5", "M5")]:
            row = QHBoxLayout()
            badge = QLabel(index)
            badge.setObjectName("mouseBadge")
            badge.setFixedWidth(24)

            button = QPushButton(label)
            button.setObjectName("mouseMapButton")
            button.clicked.connect(lambda _, name=label: self._choose_action(name, MOUSEMAP[name]))
            self.mouse_buttons[label] = button

            row.addWidget(badge)
            row.addWidget(button, 1)
            list_layout.addLayout(row)

        list_layout.addStretch(1)
        list_panel.setLayout(list_layout)
        layout.addWidget(list_panel, 1)

        mouse_visual = QFrame()
        mouse_visual.setObjectName("mouseVisual")
        visual_layout = QVBoxLayout()
        visual_layout.addWidget(self._section_title("DIAGRAMA DO MOUSE"))
        visual_grid = QGridLayout()
        visual_grid.setVerticalSpacing(10)
        visual_grid.setHorizontalSpacing(10)
        for index, label in enumerate(["LMB", "RMB", "MMB", "M4", "M5"], start=1):
            button = QPushButton(f"{index} - {label}")
            button.setObjectName("mouseNode")
            button.clicked.connect(lambda _, name=label: self._choose_action(name, MOUSEMAP[name]))
            visual_grid.addWidget(button, index - 1, 0)
        visual_layout.addLayout(visual_grid)

        hint = QLabel("Use a aba de desempenho/iluminacao no proximo milestone.")
        hint.setObjectName("hintLabel")
        visual_layout.addWidget(hint)
        visual_layout.addStretch(1)
        mouse_visual.setLayout(visual_layout)
        layout.addWidget(mouse_visual, 1)

        page.setLayout(layout)
        return page

    def _build_macros_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._section_title("MACROS"))
        hint = QLabel("Editor de macros entra no M4. A base de remap por ID ja esta pronta.")
        hint.setObjectName("hintLabel")
        layout.addWidget(hint)
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _build_device_dock(self) -> QWidget:
        dock = QFrame()
        dock.setObjectName("deviceDock")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("DISPOSITIVOS"))

        self.device_cards_row = QHBoxLayout()
        self.device_cards_row.setSpacing(8)
        layout.addLayout(self.device_cards_row, 1)
        dock.setLayout(layout)
        return dock

    def _apply_theme(self):
        self.setStyleSheet(STYLE_SHEET)

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("pageTitle")
        return label

    def _set_top_tab(self, tab_name: str):
        self.current_top_tab = tab_name
        for name, button in self.top_tabs.items():
            button.setChecked(name == tab_name)
        for name, button in self.sub_tabs.items():
            if tab_name == "MACROS":
                button.setChecked(False)
            else:
                button.setChecked(name == "PERSONALIZAR")

        if tab_name == "TECLADO":
            self.page_stack.setCurrentIndex(0)
        elif tab_name == "MOUSE":
            self.page_stack.setCurrentIndex(1)
        else:
            self.page_stack.setCurrentIndex(2)

    def _choose_action(self, label: str, fallback_code: str):
        dialog = ActionDialog(label, self)
        if dialog.exec() != QDialog.Accepted:
            return

        action = dialog.get_action()
        codes = self._codes_for_label(label, fallback_code)
        if action.type == ActionType.NONE:
            for code in codes:
                self.mappings.pop(code, None)
            self.label_actions.pop(label, None)
        else:
            for code in codes:
                self.mappings[code] = action
            self.label_actions[label] = action
        self._refresh_label_visual(label)
        self.status_label.setText(f"{label} -> {action.type.value} [{', '.join(codes)}]")

    def _refresh_label_visual(self, label: str):
        action = self.label_actions.get(label)
        mapped = action is not None and action.type != ActionType.NONE
        tooltip = label
        if label in self.key_id_map:
            learned = self.key_id_map[label]
            tooltip += f" | ID: {learned.get('symbolic')} ({learned.get('numeric')})"
        if mapped:
            tooltip += f" | Acao: {self._action_text(action)}"

        if label in self.keyboard_buttons:
            button = self.keyboard_buttons[label]
            button.setProperty("mapped", "true" if mapped else "false")
            button.setToolTip(tooltip)
            button.style().unpolish(button)
            button.style().polish(button)
        if label in self.mouse_buttons:
            button = self.mouse_buttons[label]
            action_text = self._action_text(action) if mapped else "Pass-through"
            button.setText(f"{label}  |  {action_text}")
            button.setToolTip(tooltip)

    @staticmethod
    def _action_text(action: Action | None) -> str:
        if not action:
            return "Pass-through"
        if action.type == ActionType.KEYSTROKE:
            return f"Keystroke {action.payload.get('key', '')}".strip()
        return action.type.value

    def _toggle_mx_capture(self):
        if self.capture_active:
            self._stop_capture("Escuta cancelada.")
            return
        self._start_capture(MX_CAPTURE_SEQUENCE, mode="mx")

    def _toggle_full_capture(self):
        if self.capture_active:
            self._stop_capture("Escuta cancelada.")
            return
        self._start_capture(FULL_KEY_CAPTURE_SEQUENCE, mode="full")

    def _start_capture(self, sequence: List[str], mode: str):
        device = self.device_input.text().strip()
        if not device:
            QMessageBox.warning(self, "Device", "Informe o caminho do device antes da escuta.")
            return

        self._stop()
        paths = expand_related_paths(device)
        if not paths:
            QMessageBox.warning(self, "Device", "Nenhum device de evento foi encontrado.")
            return

        self.capture_sequence = sequence
        self.capture_mode = mode
        self.capture_idx = 0
        self.capture_paths = paths
        self.capture_stop.clear()
        self.capture_active = True

        self.learn_mx_btn.setText("Parar escuta M-X")
        self.learn_all_btn.setText("Parar escuta completa")
        self._show_capture_prompt()

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _stop_capture(self, message: str = ""):
        if self.capture_active:
            self.capture_stop.set()
            self.capture_active = False

        self.learn_mx_btn.setText("Mapear M-X (escutar)")
        self.learn_all_btn.setText("Mapear teclado completo (ID)")
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=0.6)
        self.capture_thread = None
        self.capture_mode = ""
        self.capture_sequence = []
        if message:
            self.status_label.setText(message)

    def _show_capture_prompt(self):
        if self.capture_idx >= len(self.capture_sequence):
            if self.capture_mode == "full":
                self._stop_capture("Mapeamento completo finalizado.")
            else:
                self._stop_capture("Escuta M-X concluida.")
            return

        target = self.capture_sequence[self.capture_idx]
        total = len(self.capture_sequence)
        current = self.capture_idx + 1
        self.status_label.setText(f"Escutando {current}/{total}: pressione {target}.")

    def _capture_loop(self):
        devices: List[InputDevice] = []
        failures: List[str] = []
        for path in self.capture_paths:
            try:
                devices.append(InputDevice(path))
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{path}: {exc}")

        if not devices:
            self.capture_queue.put(("error", "Falha abrindo devices:\n" + "\n".join(failures)))
            return
        if failures:
            self.capture_queue.put(("warn", "Escuta parcial:\n" + "\n".join(failures)))

        try:
            while not self.capture_stop.is_set():
                readable, _, _ = select.select(devices, [], [], 0.2)
                if not readable:
                    continue
                for device in readable:
                    for event in device.read():
                        if event.type != ecodes.EV_KEY or event.value != 1:
                            continue
                        self.capture_queue.put(
                            ("hit", event_code_name(event.code), str(event.code), device.path)
                        )
        except Exception as exc:  # noqa: BLE001
            self.capture_queue.put(("error", f"Erro na escuta: {exc}"))
        finally:
            for device in devices:
                try:
                    device.close()
                except Exception:  # noqa: BLE001
                    pass

    def _poll_capture_queue(self):
        while True:
            try:
                item = self.capture_queue.get_nowait()
            except queue.Empty:
                break

            kind = item[0]
            if kind == "error":
                self._stop_capture(item[1])
                QMessageBox.critical(self, "Erro escuta", item[1])
                continue
            if kind == "warn":
                self.status_label.setText(item[1])
                continue
            if kind != "hit":
                continue
            if not self.capture_active or self.capture_idx >= len(self.capture_sequence):
                continue

            code_name, code_num, src_path = item[1], item[2], item[3]
            target = self.capture_sequence[self.capture_idx]
            self._register_learned_id(target, code_name, code_num, src_path)
            self.capture_idx += 1
            self._show_capture_prompt()

    def _register_learned_id(self, label: str, code_name: str, code_num: str, src_path: str):
        aliases = [code_name, code_num]
        for value in self.dynamic_aliases.get(label, []):
            if value not in aliases:
                aliases.append(value)
        self.dynamic_aliases[label] = aliases
        self.key_id_map[label] = {"symbolic": code_name, "numeric": code_num, "path": src_path}
        self._refresh_label_visual(label)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar mapping",
            str(Path.home() / "mapping.json"),
        )
        if not path:
            return

        save_mapping_file(
            path=path,
            device_path=self.device_input.text().strip(),
            mappings=self.mappings,
            dynamic_aliases=self.dynamic_aliases,
            key_id_map=self.key_id_map,
        )
        self.status_label.setText(f"Mapping salvo em {path}")

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carregar mapping", str(Path.home()))
        if not path:
            return

        try:
            device_path, mappings, dynamic_aliases, key_id_map = load_mapping_file(path)
            self.device_input.setText(device_path)
            self.mappings = mappings
            self.dynamic_aliases = dynamic_aliases
            self.key_id_map = key_id_map
            self._rebuild_label_actions()
            self.status_label.setText(f"Mapping carregado de {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Nao foi possivel carregar: {exc}")

    def _rebuild_label_actions(self):
        self.label_actions = {}
        for label, fallback in KEYMAP.items():
            for code in self._codes_for_label(label, fallback):
                if code in self.mappings:
                    self.label_actions[label] = self.mappings[code]
                    break
            self._refresh_label_visual(label)
        for label, fallback in MOUSEMAP.items():
            for code in self._codes_for_label(label, fallback):
                if code in self.mappings:
                    self.label_actions[label] = self.mappings[code]
                    break
            self._refresh_label_visual(label)

    def _apply(self):
        self._stop_capture()
        self._stop()
        device = self.device_input.text().strip()
        if not device:
            QMessageBox.warning(self, "Device", "Informe o caminho do device.")
            return

        paths = expand_related_paths(device)
        if not paths:
            QMessageBox.warning(self, "Device", "Nenhum device de evento foi encontrado.")
            return

        paths = self._filter_paths_for_mappings(paths)
        low_latency = is_aux_pointer_only_mapping(self.mappings)
        failures = []
        logger.info("Applying mapper with %d mapping entries", len(self.mappings))
        logger.info("Mapper paths: %s", ", ".join(paths))
        logger.info("Low-latency mode: %s", "enabled" if low_latency else "disabled")
        for path in paths:
            try:
                use_fast_mode = low_latency and "-if" in path
                mapper = InputMapper(
                    MappingConfig(
                        device_path=path,
                        mappings=self.mappings,
                        grab=not use_fast_mode,
                        passthrough=not use_fast_mode,
                    )
                )
                mapper.start()
                self.mappers.append(mapper)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{path}: {exc}")

        if not self.mappers:
            QMessageBox.critical(self, "Erro", "Falha ao iniciar remapper:\n" + "\n".join(failures))
            return
        if failures:
            QMessageBox.warning(self, "Aviso", "Interfaces nao iniciaram:\n" + "\n".join(failures))
        mode_text = " (modo baixa latencia)" if low_latency else ""
        self.status_label.setText(
            f"Remapper ativo em {len(self.mappers)} interface(s).{mode_text}"
        )

    def _stop(self):
        if not self.mappers:
            self.status_label.setText("Remapper parado.")
            return

        for mapper in self.mappers:
            mapper.stop()
        self.mappers = []
        self.status_label.setText("Remapper parado.")

    def _populate_devices(self):
        self.device_combo.clear()
        while self.device_cards_row.count():
            item = self.device_cards_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.detected_devices:
            self.device_combo.addItem("Nenhum Razer detectado")
            return

        primary_devices = []
        for path in self.detected_devices:
            self.device_combo.addItem(path)
            if path.endswith("-event-kbd") or path.endswith("-event-mouse"):
                primary_devices.append(path)

        cards = primary_devices if primary_devices else self.detected_devices[:4]
        for path in cards[:4]:
            card = QFrame()
            card.setObjectName("deviceCard")
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.addWidget(QLabel(card_name(path)))
            kind = path_kind(path)
            card_layout.addWidget(QLabel(kind.title() if kind != "unknown" else "Device"))
            card.setLayout(card_layout)
            self.device_cards_row.addWidget(card)

        self.device_input.setText(self.detected_devices[0])

    def _combo_to_input(self, idx: int):
        if idx < 0:
            return
        text = self.device_combo.itemText(idx)
        if "Nenhum Razer" not in text:
            self.device_input.setText(text)

    def _codes_for_label(self, label: str, fallback_code: str) -> List[str]:
        if label in self.dynamic_aliases:
            return self.dynamic_aliases[label]
        if fallback_code.startswith("BTN_"):
            return MOUSE_ALIASES.get(label, [fallback_code])
        return KEY_ALIASES.get(label, [fallback_code])

    def _filter_paths_for_mappings(self, paths: List[str]) -> List[str]:
        mapped_codes = extract_mapped_codes(self.mappings)
        if not mapped_codes:
            return paths

        selected: List[str] = []
        for path in paths:
            try:
                device = InputDevice(path)
                supported = set(device.capabilities(absinfo=False).get(ecodes.EV_KEY, []))
                device.close()
                if supported & mapped_codes:
                    selected.append(path)
            except Exception:  # noqa: BLE001
                # If device cannot be inspected (permissions), keep it for runtime attempt.
                selected.append(path)

        return selected or paths

    def closeEvent(self, event):
        self._stop_capture()
        self._stop()
        super().closeEvent(event)


def launch():
    verbose_input = os.getenv("SYNAPSE_VERBOSE_INPUT", "").lower() in {"1", "true", "yes", "on"}
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    if not verbose_input:
        logging.getLogger("synapse_like.remap.mapper").setLevel(logging.WARNING)

    logger.info("Starting Synapse-like GUI")
    if not verbose_input:
        logger.info("Mapper input logs em modo reduzido (set SYNAPSE_VERBOSE_INPUT=1 para debug).")
    app = QApplication.instance() or QApplication([])
    gui = RemapGUI()
    gui.show()
    app.exec()


if __name__ == "__main__":
    launch()
