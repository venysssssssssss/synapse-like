from synapse_like.gui.mapping_io import normalize_loaded_mappings
from synapse_like.remap.actions import Action, ActionType


def test_normalize_loaded_mappings_expands_alias_group():
    action = Action(ActionType.SCROLL_UP)
    mappings = {"KEY_F13": action}
    normalized = normalize_loaded_mappings(mappings, dynamic_aliases={})

    assert normalized["KEY_F13"].type == ActionType.SCROLL_UP
    assert normalized["KEY_MACRO1"].type == ActionType.SCROLL_UP
    assert normalized["183"].type == ActionType.SCROLL_UP
