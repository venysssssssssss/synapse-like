from __future__ import annotations

from typing import Dict, Set

from evdev import ecodes

from synapse_like.remap.actions import Action, ActionType

POINTER_ACTIONS = {
    ActionType.NONE,
    ActionType.SCROLL_UP,
    ActionType.SCROLL_DOWN,
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
    auxiliary_buttons = {
        ecodes.BTN_SIDE,
        ecodes.BTN_EXTRA,
        ecodes.BTN_BACK,
        ecodes.BTN_FORWARD,
    }
    for code in codes:
        if code >= f13 or code in auxiliary_buttons:
            continue
        return False
    return True


def _parse_key_code(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    if value.startswith("MSC_SCAN:") or value.startswith("MSC_SCAN_HEX:"):
        return None
    if value.startswith(("KEY_", "BTN_")):
        return ecodes.ecodes.get(value)
    return None


__all__ = ["extract_mapped_codes", "is_aux_pointer_only_mapping", "POINTER_ACTIONS"]
