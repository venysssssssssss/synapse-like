from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from synapse_like.gui.mapping_io import load_mapping_file, save_mapping_file
from synapse_like.remap.actions import Action

logger = logging.getLogger(__name__)

PROFILE_DIR = Path.home() / ".config" / "synapse-like" / "profiles"


@dataclass(slots=True)
class ProfileSummary:
    name: str
    path: Path
    linked_apps: list[str]
    device_path: str


ProfilePayload = Tuple[str, Dict[str, Action], Dict[str, List[str]], Dict[str, Dict[str, str]], List[str]]


class ProfileService:
    """Centralizes profile persistence and discovery."""

    def __init__(self, profile_dir: Path = PROFILE_DIR):
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[ProfileSummary]:
        summaries: list[ProfileSummary] = []
        for path in sorted(self.profile_dir.glob("*.json")):
            try:
                device_path, _, _, _, linked_apps = load_mapping_file(str(path))
            except Exception as exc:
                logger.warning("Skipping invalid profile %s: %s", path, exc)
                continue
            summaries.append(
                ProfileSummary(
                    name=path.stem,
                    path=path,
                    linked_apps=[app.casefold() for app in linked_apps],
                    device_path=device_path,
                )
            )
        return summaries

    def get_profile_path(self, name: str) -> Path:
        return self.profile_dir / f"{name}.json"

    def save_profile(
        self,
        filepath: str,
        device_path: str,
        mappings: Dict[str, Action],
        dynamic_aliases: Dict[str, List[str]],
        key_id_map: Dict[str, Dict[str, str]],
        linked_apps: Optional[List[str]] = None,
    ) -> None:
        save_mapping_file(
            path=filepath,
            device_path=device_path,
            mappings=mappings,
            dynamic_aliases=dynamic_aliases,
            key_id_map=key_id_map,
            linked_apps=linked_apps or [],
        )
        logger.info("Profile saved to %s", filepath)

    def save_named_profile(
        self,
        name: str,
        device_path: str,
        mappings: Dict[str, Action],
        dynamic_aliases: Dict[str, List[str]],
        key_id_map: Dict[str, Dict[str, str]],
        linked_apps: Optional[List[str]] = None,
    ) -> Path:
        path = self.get_profile_path(name)
        self.save_profile(
            filepath=str(path),
            device_path=device_path,
            mappings=mappings,
            dynamic_aliases=dynamic_aliases,
            key_id_map=key_id_map,
            linked_apps=linked_apps or [],
        )
        return path

    def load_profile(self, filepath: str) -> ProfilePayload:
        logger.info("Loading profile from %s", filepath)
        return load_mapping_file(filepath)

    def load_named_profile(self, name: str) -> ProfilePayload:
        return self.load_profile(str(self.get_profile_path(name)))

    def delete_profile(self, name: str) -> bool:
        path = self.get_profile_path(name)
        if not path.exists():
            return False
        path.unlink()
        return True

    def find_profile_for_window_class(self, wm_class: str) -> Optional[ProfileSummary]:
        normalized = wm_class.casefold().strip()
        if not normalized:
            return None
        for profile in self.list_profiles():
            if normalized in profile.linked_apps:
                return profile
        return None
