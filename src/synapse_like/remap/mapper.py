from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from evdev import InputDevice, UInput, ecodes

from synapse_like.remap.actions import Action

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MappingConfig:
    device_path: str
    mappings: Dict[str, Action] = field(default_factory=dict)
    grab: bool = True
    passthrough: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "device_path": self.device_path,
            "mappings": {key: action.to_dict() for key, action in self.mappings.items()},
            "grab": self.grab,
            "passthrough": self.passthrough,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MappingConfig":
        raw_mappings = data.get("mappings", {})
        return cls(
            device_path=str(data["device_path"]),
            mappings={
                str(key): Action.from_dict(value)
                for key, value in raw_mappings.items()
                if isinstance(value, dict)
            }
            if isinstance(raw_mappings, dict)
            else {},
            grab=bool(data.get("grab", True)),
            passthrough=bool(data.get("passthrough", True)),
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)

    @classmethod
    def load(cls, path: str) -> "MappingConfig":
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


class InputMapper:
    """
    User-space remapper that translates events from a source device to one or two
    virtual uinput devices.
    """

    def __init__(self, config: MappingConfig):
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._src: Optional[InputDevice] = None
        self._sink: Optional[UInput] = None
        self._pointer_sink: Optional[UInput] = None
        self._grabbed = False
        self._fast_code_map: Dict[int, Action] = {}
        self._fast_scan_map: Dict[int, Action] = {}
        self._name_cache: Dict[int, str] = {}
        self._debug_enabled = False
        self.active_keys: set[str] = set()
        self._build_fast_lookups()

    @property
    def device_path(self) -> str:
        return self.config.device_path

    def start(self) -> None:
        if self._running:
            return

        logger.info("Starting mapper for %s", self.config.device_path)
        self._src = InputDevice(self.config.device_path)
        if self.config.grab:
            self._src.grab()
            self._grabbed = True

        raw_caps = self._src.capabilities(absinfo=False)
        if self.config.passthrough or self._needs_keystroke_output():
            self._sink = UInput(
                self._build_caps(raw_caps),
                name=f"{self._src.name} (synapse-like)",
                bustype=self._src.info.bustype,
            )
        if self._needs_pointer_output():
            self._pointer_sink = UInput(
                self._pointer_caps(),
                name=f"{self._src.name} (synapse-like pointer)",
                bustype=self._src.info.bustype,
            )

        self._build_fast_lookups()
        self._debug_enabled = logger.isEnabledFor(logging.DEBUG)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Mapper active for %s", self.config.device_path)

    def stop(self) -> None:
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

        if self._thread:
            self._thread.join(timeout=0.3)
            self._thread = None

        if self._sink:
            self._sink.close()
        if self._pointer_sink:
            self._pointer_sink.close()

        self._src = None
        self._sink = None
        self._pointer_sink = None
        self.active_keys.clear()
        logger.info("Mapper stopped for %s", self.config.device_path)

    def _build_fast_lookups(self) -> None:
        self._fast_code_map.clear()
        self._fast_scan_map.clear()

        for key, action in self.config.mappings.items():
            if key.startswith("MSC_SCAN:"):
                try:
                    self._fast_scan_map[int(key.split(":", 1)[1])] = action
                    continue
                except ValueError:
                    continue

            if key.startswith("MSC_SCAN_HEX:"):
                try:
                    self._fast_scan_map[int(key.split(":", 1)[1], 16)] = action
                    continue
                except ValueError:
                    continue

            code = ecodes.ecodes.get(key)
            if code is None and key.isdigit():
                code = int(key)

            if code is not None:
                self._fast_code_map[code] = action

    def _loop(self) -> None:
        if self._src is None:
            return

        pending_scan: Optional[int] = None
        sink = self._sink
        debug_enabled = self._debug_enabled

        try:
            for event in self._src.read_loop():
                if not self._running:
                    break

                if event.type == ecodes.EV_MSC and event.code == ecodes.MSC_SCAN:
                    pending_scan = int(event.value)
                    continue

                if event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                    pending_scan = None

                if event.type == ecodes.EV_KEY:
                    mapping = self._resolve_mapping(
                        self._code_name(event.code),
                        event.code,
                        pending_scan,
                    )
                    self._update_active_keys(event.code, event.value)
                    if mapping is not None:
                        if debug_enabled and event.value == 1:
                            logger.debug(
                                "[%s] mapping hit: code=%s -> %s",
                                self.config.device_path,
                                event.code,
                                mapping.type_name,
                            )
                        self._handle_action(mapping, event.value)
                        continue

                if sink is not None and self.config.passthrough:
                    sink.write_event(event)
        except OSError as exc:
            if self._running:
                logger.warning("Mapper loop error on %s: %s", self.config.device_path, exc)
        except Exception as exc:
            logger.exception("Unexpected mapper error on %s: %s", self.config.device_path, exc)
        finally:
            self._running = False

    def _resolve_mapping(
        self,
        key_name: str,
        numeric_code: int,
        scan_code: Optional[int],
    ) -> Optional[Action]:
        if scan_code is not None:
            mapped = self._fast_scan_map.get(scan_code)
            if mapped is not None:
                return mapped

        mapped = self._fast_code_map.get(numeric_code)
        if mapped is not None:
            return mapped

        return self.config.mappings.get(key_name)

    def _handle_action(self, action: Action, event_value: int) -> None:
        sink = self._pointer_sink if action.strategy.prefers_pointer_output() else self._sink
        if sink is None:
            sink = self._sink or self._pointer_sink
        if sink is None:
            return
        action.strategy.execute(sink, event_value, action.strategy.to_dict())

    def _update_active_keys(self, code: int, value: int) -> None:
        name = self._code_name(code)
        if value == 1:
            self.active_keys.add(name)
        elif value == 0:
            self.active_keys.discard(name)

    def _code_name(self, code: int) -> str:
        cached = self._name_cache.get(code)
        if cached:
            return cached

        if code in ecodes.KEY:
            name = ecodes.KEY[code]
        else:
            name = str(code)
        self._name_cache[code] = name
        return name

    def _build_caps(self, raw_caps: Dict[int, Iterable[int]]) -> Dict[int, list[int]]:
        keys = set(raw_caps.get(ecodes.EV_KEY, []))
        rels = set(raw_caps.get(ecodes.EV_REL, []))

        for action in self.config.mappings.values():
            keys.update(action.strategy.required_key_codes())
            rels.update(action.strategy.required_rel_codes())

        caps: Dict[int, list[int]] = {}
        if keys:
            caps[ecodes.EV_KEY] = sorted(keys)
        if rels:
            caps[ecodes.EV_REL] = sorted(rels)
        return caps

    def _pointer_caps(self) -> Dict[int, list[int]]:
        return {
            ecodes.EV_KEY: [
                ecodes.BTN_LEFT,
                ecodes.BTN_RIGHT,
                ecodes.BTN_MIDDLE,
                ecodes.BTN_SIDE,
                ecodes.BTN_EXTRA,
            ],
            ecodes.EV_REL: [ecodes.REL_WHEEL, ecodes.REL_X, ecodes.REL_Y],
        }

    def _needs_pointer_output(self) -> bool:
        return any(action.strategy.prefers_pointer_output() for action in self.config.mappings.values())

    def _needs_keystroke_output(self) -> bool:
        return any(not action.strategy.prefers_pointer_output() for action in self.config.mappings.values())


__all__ = ["InputMapper", "MappingConfig"]
