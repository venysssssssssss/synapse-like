import json
from typing import List, Optional
from pathlib import Path
from .models import Profile

PROFILES_DIR = Path.home() / ".config" / "synapse-like" / "profiles"

def save_profile(profile: Profile):
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = PROFILES_DIR / f"{profile.name}.json"
    
    data = {
        "schema_version": profile.schema_version,
        "name": profile.name,
        "targets": profile.targets,
        "settings": profile.settings
    }
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def load_profile(name: str) -> Optional[Profile]:
    file_path = PROFILES_DIR / f"{name}.json"
    if not file_path.exists():
        return None
        
    with open(file_path, "r") as f:
        data = json.load(f)
        
    return Profile(
        schema_version=data.get("schema_version", 1),
        name=data.get("name"),
        targets=data.get("targets", []),
        settings=data.get("settings", {})
    )

def list_profiles() -> List[str]:
    if not PROFILES_DIR.exists():
        return []
    return [f.stem for f in PROFILES_DIR.glob("*.json")]
