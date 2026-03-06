from synapse_like.gui.profile_service import ProfileService
from synapse_like.remap.actions import Action, ActionType


def test_find_profile_for_window_class_matches_saved_profile(tmp_path):
    service = ProfileService(profile_dir=tmp_path)
    service.save_named_profile(
        name="Gaming",
        device_path="/dev/input/event0",
        mappings={"KEY_F13": Action(ActionType.SCROLL_UP)},
        dynamic_aliases={},
        key_id_map={},
        linked_apps=["steam", "cs2"],
    )

    profile = service.find_profile_for_window_class("Steam")

    assert profile is not None
    assert profile.name == "Gaming"
