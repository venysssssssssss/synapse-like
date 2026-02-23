from enum import Enum
from typing import Optional, Dict, Any


class ActionType(str, Enum):
    KEYSTROKE = "keystroke"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    MOUSE_BUTTON_X1 = "mouse_button_x1"
    MOUSE_BUTTON_X2 = "mouse_button_x2"
    NONE = "none"


class Action:
    """
    Represents an action assigned to a physical key or button.
    For keystrokes, payload should contain a Linux input key code (e.g., KEY_A).
    """

    def __init__(self, action_type: ActionType, payload: Optional[Dict[str, Any]] = None):
        self.type = action_type
        self.payload = payload or {}

    def to_dict(self):
        return {"type": self.type.value, "payload": self.payload}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(ActionType(data.get("type", ActionType.NONE)), data.get("payload") or {})

