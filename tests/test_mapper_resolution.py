from synapse_like.remap.actions import Action, ActionType
from synapse_like.remap.mapper import InputMapper, MappingConfig


def test_resolve_mapping_by_numeric_code():
    mapper = InputMapper(
        MappingConfig(
            device_path="/dev/null",
            mappings={"183": Action(ActionType.SCROLL_UP)},
        )
    )
    result = mapper._resolve_mapping("KEY_F13", 183, None)
    assert result is not None
    assert result.type == ActionType.SCROLL_UP


def test_resolve_mapping_by_scan_code():
    mapper = InputMapper(
        MappingConfig(
            device_path="/dev/null",
            mappings={"MSC_SCAN:70068": Action(ActionType.SCROLL_UP)},
        )
    )
    result = mapper._resolve_mapping("KEY_F13", 183, 70068)
    assert result is not None
    assert result.type == ActionType.SCROLL_UP
