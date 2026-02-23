from synapse_like.remap.actions import Action, ActionType
from synapse_like.remap.strategy import extract_mapped_codes, is_aux_pointer_only_mapping


def test_extract_mapped_codes_parses_key_aliases():
    mappings = {
        "KEY_F13": Action(ActionType.SCROLL_UP),
        "183": Action(ActionType.SCROLL_UP),
        "MSC_SCAN:70068": Action(ActionType.SCROLL_UP),
    }
    codes = extract_mapped_codes(mappings)
    assert 183 in codes
    assert len(codes) == 1


def test_aux_pointer_only_mapping_true_for_macro_scroll():
    mappings = {
        "KEY_F13": Action(ActionType.SCROLL_UP),
        "KEY_F14": Action(ActionType.SCROLL_DOWN),
    }
    assert is_aux_pointer_only_mapping(mappings) is True


def test_aux_pointer_only_mapping_false_for_regular_key_remap():
    mappings = {
        "KEY_A": Action(ActionType.KEYSTROKE, {"key": "KEY_B"}),
    }
    assert is_aux_pointer_only_mapping(mappings) is False
