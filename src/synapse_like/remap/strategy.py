from typing import Dict, Set

from evdev import ecodes

from synapse_like.remap.actions import Action, ActionType

POINTER_ACTIONS = {
    ActionType.SCROLL_UP,
    ActionType.SCROLL_DOWN,
    ActionType.MOUSE_BUTTON_X1,
    ActionType.MOUSE_BUTTON_X2,
    ActionType.NONE,
}


def extract_mapped_codes(mappings: Dict[str, Action]) -> Set[int]:
    key_codes: Set[int] = set()
    for code in mappings.keys():
        numeric = _parse_key_code(code)
        if numeric is not None:
            key_codes.add(numeric)
    return key_codes


def is_aux_pointer_only_mapping(mappings: Dict[str, Action]) -> bool:
    if not mappings:
        return False
    if any(action.type not in POINTER_ACTIONS for action in mappings.values()):
        return False

    codes = extract_mapped_codes(mappings)
    if not codes:
        return False

    f13 = ecodes.ecodes.get("KEY_F13", 183)
    for code in codes:
        if code >= f13:
            continue
        if code in {
            ecodes.BTN_SIDE,
            ecodes.BTN_EXTRA,
            ecodes.BTN_BACK,
            ecodes.BTN_FORWARD,
        }:
            continue
        return False
    return True


def _parse_key_code(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    if value.startswith(("KEY_", "BTN_")):
        return ecodes.ecodes.get(value)
    return None
