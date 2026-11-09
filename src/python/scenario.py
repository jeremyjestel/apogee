"""Parameter conversion and the versioned scenario format, independent of Qt."""

from __future__ import annotations

import json
import math

import apogee


# C++ owns parameter names, units, paths, and defaults.
PARAMETER_SPECS = apogee.parameter_specs()
SCENARIO_VERSION = 1
ENTITY_TYPES = ("radar", "interceptor", "missile", "satellite")


def default_parameter_values(params=None):
    params = apogee.Params() if params is None else params
    return {
        spec.path: str(apogee.get_parameter(params, spec.path))
        for spec in apogee.parameter_specs(params)
    }


def _parameter_value(spec, value):
    if spec.value_type == "bool":
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
        raise ValueError(f"{spec.path} must be true or false.")
    if spec.value_type == "string":
        return str(value).strip()
    if spec.value_type == "int":
        return int(float(value))

    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{spec.path} must have a numeric value.")
    try:
        numeric = float(value)
    except (ValueError, OverflowError):
        numeric = math.nan
    if not math.isfinite(numeric):
        raise ValueError(f"{spec.path} must have a finite numeric value.")
    if spec.path.endswith((".blast_radius", ".size_radius")) and numeric < 0.0:
        raise ValueError(f"{spec.path} must be non-negative.")
    return numeric


def validated_parameter_values(values, params=None):
    """Return validated parameter text for a complete set, preserving formatting."""
    if not isinstance(values, dict):
        raise ValueError("Scenario parameters must be an object of parameter paths and values.")

    specs = PARAMETER_SPECS if params is None else apogee.parameter_specs(params)
    expected = {spec.path for spec in specs}
    missing = expected - values.keys()
    unknown = values.keys() - expected
    if missing or unknown:
        details = []
        if missing:
            details.append("Missing parameters: " + ", ".join(sorted(missing)))
        if unknown:
            details.append("Unknown parameters: " + ", ".join(sorted(map(str, unknown))))
        raise ValueError("\n".join(details))

    result = {}
    for spec in specs:
        value = values[spec.path]
        _parameter_value(spec, value)
        result[spec.path] = str(value)
    return result


def require_entity_types(params):
    present = {entity.type for entity in params.entities}
    missing = [kind for kind in ENTITY_TYPES if kind not in present]
    if missing:
        raise ValueError("Scenario requires at least one of each entity type. Missing: " + ", ".join(missing))


def create_params_from_text(values, params=None):
    """Validate all inputs before creating the parameters used by a simulation."""
    params = apogee.Params() if params is None else apogee.Params(params)
    require_entity_types(params)
    values = validated_parameter_values(values, params)
    for spec in apogee.parameter_specs(params):
        apogee.set_parameter(params, spec.path, _parameter_value(spec, values[spec.path]))
    return params


def encode_scenario(values, params=None):
    scenario = {
        "version": SCENARIO_VERSION if params is None else 2,
        "parameters": validated_parameter_values(values, params),
    }
    if params is not None:
        require_entity_types(params)
        scenario["entities"] = [
            dict(id=entity.id, key=entity.key, display_name=entity.display_name,
                 type=entity.type, team=entity.team,
                 **({"target_key": entity.initial_pursuit.target_key}
                    if entity.type in ("missile", "interceptor") else {}))
            for entity in params.entities
        ]
    return json.dumps(scenario, indent=2) + "\n"


def decode_scenario_definition(text):
    scenario = json.loads(text)
    if not isinstance(scenario, dict) or type(scenario.get("version")) is not int:
        raise ValueError("This file is not an Apogee scenario.")
    if scenario["version"] not in (1, 2):
        raise ValueError("This scenario file version is not supported.")
    params = apogee.Params()
    if scenario["version"] == 2:
        definitions = scenario.get("entities")
        if not isinstance(definitions, list):
            raise ValueError("Scenario entities must be a list.")
        entities = []
        for definition in definitions:
            entity = apogee.make_entity_definition(
                definition["type"], definition["key"], definition["id"]
            )
            entity.display_name = definition["display_name"]
            entity.team = definition["team"]
            if entity.type in ("missile", "interceptor") and "target_key" in definition:
                entity.initial_pursuit.target_key = definition["target_key"]
            entities.append(entity)
        params.entities = entities
        require_entity_types(params)
    parameters = scenario.get("parameters")
    if isinstance(parameters, dict):
        # Supply defaults for settings introduced after a scenario was saved.
        parameters = parameters.copy()
        processing_suffixes = (".radar.pulse_num", ".radar.range_window", ".radar.doppler_window")
        for path, value in default_parameter_values(params).items():
            if (path.endswith((".active", ".blast_radius", ".size_radius", ".radar.doppler_zero_pad_factor", ".initial_pursuit.guidance_gain")) or
                    scenario["version"] == 1 and path.endswith(processing_suffixes)):
                parameters.setdefault(path, value)
    return params, validated_parameter_values(parameters, params)


def decode_scenario(text):
    return decode_scenario_definition(text)[1]
