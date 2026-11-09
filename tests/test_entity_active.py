import json
from pathlib import Path

import apogee
import pytest

from scenario import (create_params_from_text, decode_scenario_definition,
                      default_parameter_values, encode_scenario)


def test_active_is_available_for_every_entity_type_and_round_trips():
    params = apogee.Params()
    specs = {spec.path: spec for spec in apogee.parameter_specs(params)}
    values = default_parameter_values(params)
    for entity in params.entities:
        path = f"{entity.key}.active"
        assert specs[path].value_type == "bool"
        assert entity.active is True
        values[path] = "false"
    disabled = create_params_from_text(values, params)
    assert all(entity.active is False for entity in disabled.entities)
    restored_params, restored = decode_scenario_definition(encode_scenario(values, disabled))
    assert all(not entity.active for entity in create_params_from_text(restored, restored_params).entities)
    # Direct Python edits feed the same parameter path.
    params.entity("red_missile").active = False
    assert apogee.get_parameter(params, "red_missile.active") is False


@pytest.mark.parametrize("version", [1, 2])
def test_older_scenarios_default_to_active(version):
    params = apogee.Params()
    data = json.loads(encode_scenario(default_parameter_values(params), params if version == 2 else None))
    data["parameters"] = {key: value for key, value in data["parameters"].items() if not key.endswith(".active")}
    definitions, values = decode_scenario_definition(json.dumps(data))
    assert all(entity.active for entity in create_params_from_text(values, definitions).entities)


@pytest.mark.parametrize("value", [False, "false", "False", "0", 0])
def test_active_accepts_false_values(value):
    values = default_parameter_values()
    values["red_missile.active"] = value
    assert create_params_from_text(values).entity("red_missile").active is False


@pytest.mark.parametrize("value", ["disabled", "2", None])
def test_active_rejects_ambiguous_values(value):
    values = default_parameter_values()
    values["red_missile.active"] = value
    with pytest.raises(ValueError, match="true or false"):
        create_params_from_text(values)


def test_all_checked_in_scenarios_load():
    for path in (Path(__file__).resolve().parents[1] / "scenarios").glob("*.json"):
        params, values = decode_scenario_definition(path.read_text(encoding="utf-8-sig"))
        assert all(entity.active for entity in create_params_from_text(values, params).entities)


def test_disabled_scene_logs_frozen_states_and_activity():
    params = apogee.Params()
    params.simulation.duration_s = 0.2
    for entity in params.entities:
        params.entity(entity.key).active = False
    result = apogee.run_sim(params)
    activity = [item for item in result.scalars if item.system == "entity" and item.key == "active"]
    assert len(activity) == len(params.entities)
    assert all(item.values == [0.0, 0.0, 0.0] for item in activity)
    for item in result.vectors:
        if item.system == "kinematics":
            coordinates = [(v.x, v.y, v.z) for v in item.values]
            assert coordinates == [coordinates[0]] * 3
