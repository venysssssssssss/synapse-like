from synapse_like.remap.actions import Action, ActionType


def test_action_roundtrip_preserves_macro_payload():
    action = Action(
        ActionType.MACRO,
        {
            "events": [
                {"type": "key", "code": "KEY_A", "state": 1},
                {"type": "delay", "value": 25},
                {"type": "key", "code": "KEY_A", "state": 0},
            ]
        },
    )

    restored = Action.from_dict(action.to_dict())

    assert restored.type == ActionType.MACRO
    assert restored.strategy.events[1]["value"] == 25
