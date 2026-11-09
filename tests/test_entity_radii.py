import json

import apogee
import pytest

from scenario import (create_params_from_text, decode_scenario_definition,
                      default_parameter_values, encode_scenario)


DEFAULTS = {"radar": (0.0, 10.0), "satellite": (0.0, 5.0),
            "missile": (50.0, 2.0), "interceptor": (25.0, 1.0)}


def test_default_and_added_entities_expose_radii_parameters():
    params = apogee.Params()
    specs = {item.path: item for item in apogee.parameter_specs(params)}
    for entity in params.entities:
        assert (entity.blast_radius, entity.size_radius) == DEFAULTS[entity.type]
        for field in ("blast_radius", "size_radius"):
            assert specs[f"{entity.key}.{field}"].unit == "m"
        added = apogee.make_entity_definition(entity.type, "extra", 10)
        assert (added.blast_radius, added.size_radius) == DEFAULTS[entity.type]


@pytest.mark.parametrize("version", [1, 2])
def test_radii_round_trip_and_older_scenario_defaults(version):
    params = apogee.Params()
    values = default_parameter_values(params)
    values["blue_interceptor.blast_radius"] = " 40.00 "
    values["blue_interceptor.size_radius"] = "1.5"
    encoded = encode_scenario(values, params if version == 2 else None)
    definitions, restored = decode_scenario_definition(encoded)
    rebuilt = create_params_from_text(restored, definitions)
    assert restored == values
    assert rebuilt.entity("blue_interceptor").blast_radius == 40.0
    assert rebuilt.entity("blue_interceptor").size_radius == 1.5
    legacy = json.loads(encoded)
    legacy["parameters"] = {key: value for key, value in legacy["parameters"].items()
                            if not key.endswith((".blast_radius", ".size_radius"))}
    definitions, restored = decode_scenario_definition(json.dumps(legacy))
    for entity in create_params_from_text(restored, definitions).entities:
        assert (entity.blast_radius, entity.size_radius) == DEFAULTS[entity.type]


@pytest.mark.parametrize("field", ["blast_radius", "size_radius"])
def test_negative_radii_are_rejected(field):
    values = default_parameter_values()
    values[f"red_missile.{field}"] = "-1"
    with pytest.raises(ValueError, match="non-negative"):
        create_params_from_text(values)
