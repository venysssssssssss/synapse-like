import os
from glob import glob
from typing import List


def detect_razer_devices() -> List[str]:
    patterns = [
        "/dev/input/by-id/*Razer*-event-kbd",
        "/dev/input/by-id/*Razer*-event-mouse",
        "/dev/input/by-id/*Razer*-event-if*",
        "/dev/input/by-path/*-razer-*event*",
    ]
    found: List[str] = []
    for pattern in patterns:
        found.extend(path for path in glob(pattern) if os.path.exists(path))
    return _unique(found)


def expand_related_paths(selected_path: str) -> List[str]:
    if "/dev/input/by-id/" not in selected_path or "-event" not in selected_path:
        return [selected_path]

    prefix = selected_path.split("-event", 1)[0]
    base = prefix.split("-if", 1)[0]
    patterns = [f"{base}-event*", f"{base}-if*-event*"]

    matches: List[str] = []
    for pattern in patterns:
        matches.extend(path for path in sorted(glob(pattern)) if os.path.exists(path))
    matches = _unique(matches)
    if selected_path not in matches:
        matches.insert(0, selected_path)

    target_kind = path_kind(selected_path)
    if target_kind == "keyboard":
        keyboard_paths = [path for path in matches if path_kind(path) == "keyboard"]
        if keyboard_paths:
            return keyboard_paths
    if target_kind == "mouse":
        mouse_paths = [path for path in matches if path_kind(path) == "mouse"]
        if mouse_paths:
            return mouse_paths

    return matches


def path_kind(path: str) -> str:
    if "-kbd" in path:
        return "keyboard"
    if "-mouse" in path:
        return "mouse"
    return "unknown"


def card_name(path: str) -> str:
    name = path.split("/")[-1]
    return name.replace("usb-", "").replace("-event-kbd", "").replace("-event-mouse", "")


def _unique(items: List[str]) -> List[str]:
    unique: List[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return unique
