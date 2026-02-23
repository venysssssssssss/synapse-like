import json
from typing import Dict, List, Tuple

from synapse_like.gui.constants import KEY_ALIASES, MOUSE_ALIASES
from synapse_like.remap.actions import Action


def save_mapping_file(
    path: str,
    device_path: str,
    mappings: Dict[str, Action],
    dynamic_aliases: Dict[str, List[str]],
    key_id_map: Dict[str, Dict[str, str]],
) -> None:
    data = {
        "version": 2,
        "device_path": device_path,
        "mappings": {code: action.to_dict() for code, action in mappings.items()},
        "dynamic_aliases": dynamic_aliases,
        "key_id_map": key_id_map,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def load_mapping_file(
    path: str,
) -> Tuple[str, Dict[str, Action], Dict[str, List[str]], Dict[str, Dict[str, str]]]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    loaded_mappings: Dict[str, Action] = {}
    for code, payload in raw.get("mappings", {}).items():
        if isinstance(payload, dict) and "type" in payload:
            loaded_mappings[code] = Action.from_dict(payload)

    dynamic_aliases = _sanitize_aliases(raw.get("dynamic_aliases", {}))
    key_id_map = _sanitize_key_id_map(raw.get("key_id_map", {}))

    normalized = normalize_loaded_mappings(loaded_mappings, dynamic_aliases)
    device_path = str(raw.get("device_path", ""))
    return device_path, normalized, dynamic_aliases, key_id_map


def normalize_loaded_mappings(
    mappings: Dict[str, Action],
    dynamic_aliases: Dict[str, List[str]],
) -> Dict[str, Action]:
    alias_groups = (
        list(KEY_ALIASES.values())
        + list(MOUSE_ALIASES.values())
        + list(dynamic_aliases.values())
    )
    normalized: Dict[str, Action] = {}
    for code, action in mappings.items():
        expanded = [code]
        for group in alias_groups:
            if code in group:
                expanded = group
                break
        for key_code in expanded:
            normalized[key_code] = action
    return normalized


def _sanitize_aliases(raw_aliases: object) -> Dict[str, List[str]]:
    if not isinstance(raw_aliases, dict):
        return {}
    sanitized: Dict[str, List[str]] = {}
    for label, aliases in raw_aliases.items():
        if isinstance(label, str) and isinstance(aliases, list):
            sanitized[label] = [str(alias) for alias in aliases if isinstance(alias, (str, int))]
    return sanitized


def _sanitize_key_id_map(raw_map: object) -> Dict[str, Dict[str, str]]:
    if not isinstance(raw_map, dict):
        return {}
    sanitized: Dict[str, Dict[str, str]] = {}
    for label, payload in raw_map.items():
        if not isinstance(label, str) or not isinstance(payload, dict):
            continue
        entry: Dict[str, str] = {}
        for field in ("symbolic", "numeric", "path", "scan"):
            value = payload.get(field)
            if value is not None:
                entry[field] = str(value)
        sanitized[label] = entry
    return sanitized
