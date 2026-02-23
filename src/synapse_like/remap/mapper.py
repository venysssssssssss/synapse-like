import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict

from evdev import InputDevice, UInput, ecodes

from synapse_like.remap.actions import Action, ActionType

logger = logging.getLogger(__name__)


@dataclass
class MappingConfig:
    device_path: str
    mappings: Dict[str, Action] = field(default_factory=dict)  # physical key -> Action
    grab: bool = True
    passthrough: bool = True

    def to_dict(self):
        return {
            "device_path": self.device_path,
            "mappings": {k: v.to_dict() for k, v in self.mappings.items()},
            "grab": self.grab,
            "passthrough": self.passthrough,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            device_path=data["device_path"],
            mappings={k: Action.from_dict(v) for k, v in data.get("mappings", {}).items()},
            grab=bool(data.get("grab", True)),
            passthrough=bool(data.get("passthrough", True)),
        )

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))


class InputMapper:
    """
    Simple user-space remapper: grabs an input device, emits to a uinput
    virtual device applying the configured actions.
    Requires read/write access to /dev/input and uinput.
    """

    def __init__(self, config: MappingConfig):
        self.config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._src: InputDevice | None = None
        self._sink: UInput | None = None
        self._pointer_sink: UInput | None = None
        self._name_cache: Dict[int, str] = {}
        self._grabbed = False

    def start(self):
        if self._running:
            return
        logger.info("Starting mapper for %s", self.config.device_path)
        # Initialize source and uinput synchronously so errors are visible to GUI.
        self._src = InputDevice(self.config.device_path)
        if self.config.grab:
            self._src.grab()
            self._grabbed = True

        raw_caps = self._src.capabilities(absinfo=False)
        if self.config.passthrough or self._needs_keystroke_output():
            capabilities = self._build_caps(raw_caps)
            self._sink = UInput(
                capabilities,
                name=f"{self._src.name} (synapse-like)",
                bustype=self._src.info.bustype,
            )
        if self._needs_pointer_output():
            self._pointer_sink = UInput(
                self._pointer_caps(),
                name=f"{self._src.name} (synapse-like pointer)",
                bustype=self._src.info.bustype,
            )

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Mapper active for %s", self.config.device_path)

    def stop(self):
        self._running = False
        if self._src:
            if self._grabbed:
                try:
                    self._src.ungrab()
                except Exception:
                    pass
                self._grabbed = False
            try:
                self._src.close()
            except Exception:
                pass
            self._src = None
        if self._thread:
            self._thread.join(timeout=0.2)
            self._thread = None
        if self._sink:
            self._sink.close()
            self._sink = None
        if self._pointer_sink:
            self._pointer_sink.close()
            self._pointer_sink = None
        logger.info("Mapper stopped for %s", self.config.device_path)

    # Internal helpers
    def _loop(self):
        pending_scan: int | None = None
        sink = self._sink
        try:
            for event in self._src.read_loop():
                if not self._running:
                    break
                if event.type == ecodes.EV_MSC and event.code == ecodes.MSC_SCAN:
                    pending_scan = int(event.value)
                    logger.debug(
                        "[%s] msc scan: dec=%s hex=%s",
                        self.config.device_path,
                        pending_scan,
                        format(pending_scan, "x"),
                    )
                    continue
                if event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                    pending_scan = None
                if event.type == ecodes.EV_KEY:
                    code_str = self._code_name(event.code)
                    if event.value == 1:
                        logger.debug(
                            "[%s] key down: code=%s (%s)",
                            self.config.device_path,
                            event.code,
                            code_str,
                        )
                    mapping = self._resolve_mapping(code_str, event.code, pending_scan)
                    if mapping:
                        if event.value == 1:
                            logger.debug(
                                "[%s] mapping hit: %s/%s -> %s",
                                self.config.device_path,
                                code_str,
                                event.code,
                                mapping.type.value,
                            )
                        self._handle_action(mapping, event)
                        continue

                # Default passthrough
                if sink is not None and self.config.passthrough:
                    sink.write_event(event)
        except OSError as exc:
            if self._running:
                logger.warning("Mapper loop error on %s: %s", self.config.device_path, exc)
        except Exception as exc:
            logger.exception("Unexpected mapper error on %s: %s", self.config.device_path, exc)
        finally:
            self._running = False

    def _resolve_mapping(self, code_name: str, code_num: int, scan: int | None) -> Action | None:
        candidates = [code_name, str(code_num)]
        if scan is not None:
            scan_hex = format(scan, "x")
            candidates.extend(
                [
                    f"MSC_SCAN:{scan}",
                    f"MSC_SCAN:{scan_hex}",
                    f"MSC_SCAN:0x{scan_hex}",
                    f"MSC_SCAN_HEX:{scan_hex}",
                    scan_hex,
                ]
            )
        for key in candidates:
            action = self.config.mappings.get(key)
            if action:
                return action
        return None

    def _code_name(self, code: int) -> str:
        """Return a stable name for a key/button code."""
        cached = self._name_cache.get(code)
        if cached:
            return cached

        if code in ecodes.KEY:
            name = ecodes.KEY[code]
            self._name_cache[code] = name
            return name

        for name, value in ecodes.ecodes.items():
            if value == code:
                self._name_cache[code] = name
                return name

        unknown = str(code)
        self._name_cache[code] = unknown
        return unknown

    def _handle_action(self, action: Action, event):
        """Apply action based on incoming key event."""
        if action.type == ActionType.NONE:
            logger.debug("[%s] action none (drop event)", self.config.device_path)
            return

        if action.type == ActionType.KEYSTROKE:
            target = action.payload.get("key")
            if target:
                code = ecodes.ecodes.get(target)
                if code:
                    sink = self._sink
                    if sink is None:
                        logger.warning(
                            "[%s] no keyboard sink for keystroke emission",
                            self.config.device_path,
                        )
                        return
                    sink.write(ecodes.EV_KEY, code, event.value)
                    sink.syn()
                    if event.value == 1:
                        logger.debug(
                            "[%s] emitted keystroke: %s",
                            self.config.device_path,
                            target,
                        )
                else:
                    logger.warning("[%s] unknown keystroke target: %s", self.config.device_path, target)
            return

        if event.value != 1:  # only act on key-down for other actions
            return

        if action.type == ActionType.SCROLL_UP:
            sink = self._pointer_sink or self._sink
            if sink is None:
                return
            sink.write(ecodes.EV_REL, ecodes.REL_WHEEL, 1)
            logger.debug("[%s] emitted scroll up", self.config.device_path)
        elif action.type == ActionType.SCROLL_DOWN:
            sink = self._pointer_sink or self._sink
            if sink is None:
                return
            sink.write(ecodes.EV_REL, ecodes.REL_WHEEL, -1)
            logger.debug("[%s] emitted scroll down", self.config.device_path)
        elif action.type == ActionType.MOUSE_BUTTON_X1:
            sink = self._pointer_sink or self._sink
            if sink is None:
                return
            sink.write(ecodes.EV_KEY, ecodes.BTN_SIDE, 1)
            sink.write(ecodes.EV_KEY, ecodes.BTN_SIDE, 0)
            logger.debug("[%s] emitted mouse button X1", self.config.device_path)
        elif action.type == ActionType.MOUSE_BUTTON_X2:
            sink = self._pointer_sink or self._sink
            if sink is None:
                return
            sink.write(ecodes.EV_KEY, ecodes.BTN_EXTRA, 1)
            sink.write(ecodes.EV_KEY, ecodes.BTN_EXTRA, 0)
            logger.debug("[%s] emitted mouse button X2", self.config.device_path)

        sink = self._pointer_sink or self._sink
        sink.syn()

    def _build_caps(self, raw_caps):
        """
        Build a clean capabilities dict for uinput with only EV_KEY/EV_REL
        and inject required extra codes.
        """
        keys = set(raw_caps.get(ecodes.EV_KEY, []))
        rels = set(raw_caps.get(ecodes.EV_REL, []))

        # Add requirements based on configured actions
        for action in self.config.mappings.values():
            if action.type == ActionType.KEYSTROKE:
                target = action.payload.get("key")
                code = ecodes.ecodes.get(target) if target else None
                if code:
                    keys.add(code)
            elif action.type == ActionType.MOUSE_BUTTON_X1:
                keys.add(ecodes.BTN_SIDE)
            elif action.type == ActionType.MOUSE_BUTTON_X2:
                keys.add(ecodes.BTN_EXTRA)
            elif action.type == ActionType.SCROLL_UP or action.type == ActionType.SCROLL_DOWN:
                rels.add(ecodes.REL_WHEEL)

        caps = {}
        if keys:
            caps[ecodes.EV_KEY] = list(keys)
        if rels:
            caps[ecodes.EV_REL] = list(rels)
        return caps

    def _pointer_caps(self):
        rels = [ecodes.REL_WHEEL, ecodes.REL_X, ecodes.REL_Y]
        return {
            ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE, ecodes.BTN_SIDE, ecodes.BTN_EXTRA],
            ecodes.EV_REL: rels,
        }

    def _needs_pointer_output(self) -> bool:
        for action in self.config.mappings.values():
            if action.type in {
                ActionType.SCROLL_UP,
                ActionType.SCROLL_DOWN,
                ActionType.MOUSE_BUTTON_X1,
                ActionType.MOUSE_BUTTON_X2,
            }:
                return True
        return False

    def _needs_keystroke_output(self) -> bool:
        for action in self.config.mappings.values():
            if action.type == ActionType.KEYSTROKE:
                return True
        return False
