from __future__ import annotations

import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional, Type

from evdev import ecodes


class ActionType(str, Enum):
    NONE = "none"
    KEYSTROKE = "keystroke"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    MACRO = "macro"
    LAUNCH_APP = "launch_app"


class ActionStrategy(ABC):
    type_name: ClassVar[str] = ActionType.NONE.value

    @abstractmethod
    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        """Executes the action against a writable input sink."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the strategy payload."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ActionStrategy":
        """Rebuilds the strategy from serialized payload."""

    def prefers_pointer_output(self) -> bool:
        return False

    def required_key_codes(self) -> Iterable[int]:
        return ()

    def required_rel_codes(self) -> Iterable[int]:
        return ()


@dataclass(slots=True)
class NoneActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.NONE.value

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        return

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NoneActionStrategy":
        return cls()


@dataclass(slots=True)
class KeystrokeActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.KEYSTROKE.value
    key: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        if uinput_device is None or not self.key:
            return

        key_code = ecodes.ecodes.get(self.key)
        if key_code is None:
            return

        modifier_codes = [
            code
            for code in (ecodes.ecodes.get(name) for name in self.modifiers)
            if code is not None
        ]

        if event_value == 1:
            for modifier in modifier_codes:
                uinput_device.write(ecodes.EV_KEY, modifier, 1)
            uinput_device.write(ecodes.EV_KEY, key_code, 1)
            uinput_device.syn()
            return

        if event_value == 0:
            uinput_device.write(ecodes.EV_KEY, key_code, 0)
            for modifier in reversed(modifier_codes):
                uinput_device.write(ecodes.EV_KEY, modifier, 0)
            uinput_device.syn()

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "modifiers": list(self.modifiers)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "KeystrokeActionStrategy":
        modifiers = [str(value) for value in data.get("modifiers", []) if isinstance(value, str)]
        key = data.get("key")
        return cls(key=str(key) if isinstance(key, str) and key else None, modifiers=modifiers)

    def required_key_codes(self) -> Iterable[int]:
        codes: list[int] = []
        for name in [*self.modifiers, self.key]:
            if not name:
                continue
            code = ecodes.ecodes.get(name)
            if code is not None:
                codes.append(code)
        return codes


@dataclass(slots=True)
class ScrollUpActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.SCROLL_UP.value

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        if uinput_device is None or event_value != 1:
            return
        uinput_device.write(ecodes.EV_REL, ecodes.REL_WHEEL, 1)
        uinput_device.syn()

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ScrollUpActionStrategy":
        return cls()

    def prefers_pointer_output(self) -> bool:
        return True

    def required_rel_codes(self) -> Iterable[int]:
        return (ecodes.REL_WHEEL,)


@dataclass(slots=True)
class ScrollDownActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.SCROLL_DOWN.value

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        if uinput_device is None or event_value != 1:
            return
        uinput_device.write(ecodes.EV_REL, ecodes.REL_WHEEL, -1)
        uinput_device.syn()

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ScrollDownActionStrategy":
        return cls()

    def prefers_pointer_output(self) -> bool:
        return True

    def required_rel_codes(self) -> Iterable[int]:
        return (ecodes.REL_WHEEL,)


@dataclass(slots=True)
class MacroActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.MACRO.value
    events: list[Dict[str, Any]] = field(default_factory=list)

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        if uinput_device is None or event_value != 1 or not self.events:
            return
        threading.Thread(target=self._run, args=(uinput_device,), daemon=True).start()

    def _run(self, uinput_device: Any) -> None:
        for event in self.events:
            event_type = event.get("type")
            if event_type == "delay":
                delay_ms = int(event.get("value", 0))
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)
                continue

            if event_type != "key":
                continue

            code_name = event.get("code")
            if not isinstance(code_name, str):
                continue

            code = ecodes.ecodes.get(code_name)
            if code is None:
                continue

            state = int(event.get("state", 1))
            uinput_device.write(ecodes.EV_KEY, code, state)
            uinput_device.syn()

    def to_dict(self) -> Dict[str, Any]:
        return {"events": [dict(event) for event in self.events]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MacroActionStrategy":
        raw_events = data.get("events", [])
        if not isinstance(raw_events, list):
            raw_events = []
        return cls(events=[dict(event) for event in raw_events if isinstance(event, Mapping)])

    def required_key_codes(self) -> Iterable[int]:
        codes: list[int] = []
        for event in self.events:
            if event.get("type") != "key":
                continue
            code_name = event.get("code")
            if not isinstance(code_name, str):
                continue
            code = ecodes.ecodes.get(code_name)
            if code is not None:
                codes.append(code)
        return codes


@dataclass(slots=True)
class LaunchAppActionStrategy(ActionStrategy):
    type_name: ClassVar[str] = ActionType.LAUNCH_APP.value
    command: str = ""

    def execute(self, uinput_device: Any, event_value: int, payload: Dict[str, Any]) -> None:
        if event_value != 1 or not self.command.strip():
            return
        subprocess.Popen(self.command, shell=True)

    def to_dict(self) -> Dict[str, Any]:
        return {"command": self.command}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LaunchAppActionStrategy":
        command = data.get("command", "")
        return cls(command=str(command) if command else "")


ACTION_STRATEGY_MAP: Dict[str, Type[ActionStrategy]] = {
    ActionType.NONE.value: NoneActionStrategy,
    ActionType.KEYSTROKE.value: KeystrokeActionStrategy,
    ActionType.SCROLL_UP.value: ScrollUpActionStrategy,
    ActionType.SCROLL_DOWN.value: ScrollDownActionStrategy,
    ActionType.MACRO.value: MacroActionStrategy,
    ActionType.LAUNCH_APP.value: LaunchAppActionStrategy,
}


class Action:
    def __init__(
        self,
        type_or_strategy: ActionType | ActionStrategy = ActionType.NONE,
        payload: Optional[Mapping[str, Any]] = None,
        *,
        strategy: Optional[ActionStrategy] = None,
    ) -> None:
        if strategy is not None:
            self.strategy = strategy
            return

        if isinstance(type_or_strategy, ActionStrategy):
            self.strategy = type_or_strategy
            return

        action_type = (
            type_or_strategy
            if isinstance(type_or_strategy, ActionType)
            else ActionType(str(type_or_strategy))
        )
        strategy_class = ACTION_STRATEGY_MAP[action_type.value]
        self.strategy = strategy_class.from_dict(payload or {})

    @property
    def type(self) -> ActionType:
        try:
            return ActionType(self.strategy.type_name)
        except ValueError:
            return ActionType.NONE

    @property
    def type_name(self) -> str:
        return self.strategy.type_name

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.strategy.type_name, "payload": self.strategy.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Action":
        type_name = str(data.get("type", ActionType.NONE.value))
        payload = data.get("payload", {})
        strategy_class = ACTION_STRATEGY_MAP.get(type_name, NoneActionStrategy)
        payload_mapping = payload if isinstance(payload, Mapping) else {}
        return cls(strategy=strategy_class.from_dict(payload_mapping))


__all__ = [
    "ACTION_STRATEGY_MAP",
    "Action",
    "ActionStrategy",
    "ActionType",
    "KeystrokeActionStrategy",
    "LaunchAppActionStrategy",
    "MacroActionStrategy",
    "NoneActionStrategy",
    "ScrollDownActionStrategy",
    "ScrollUpActionStrategy",
]
