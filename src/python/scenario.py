"""Parameter conversion and the versioned scenario format, independent of Qt."""

from __future__ import annotations

import json
import math

import apogee


# C++ owns parameter names, units, paths, and defaults.
PARAMETER_SPECS = apogee.parameter_specs()
SCENARIO_VERSION = 1


def default_parameter_values():
    params = apogee.Params()
    return {
        spec.path: str(apogee.get_parameter(params, spec.path))
        for spec in PARAMETER_SPECS
    }


def validated_parameter_values(values):
    """Return finite numeric text for a complete parameter set, preserving formatting."""
    if not isinstance(values, dict):
        raise ValueError("Scenario parameters must be an object of parameter paths and values.")

    expected = {spec.path for spec in PARAMETER_SPECS}
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
    for spec in PARAMETER_SPECS:
        value = values[spec.path]
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError(f"{spec.path} must have a numeric value.")
        try:
            finite = math.isfinite(float(value))
        except (ValueError, OverflowError):
            finite = False
        if not finite:
            raise ValueError(f"{spec.path} must have a finite numeric value.")
        result[spec.path] = str(value)
    return result


def create_params_from_text(values):
    """Validate all inputs before creating the parameters used by a simulation."""
    values = validated_parameter_values(values)
    params = apogee.Params()
    for path, value in values.items():
        apogee.set_parameter(params, path, float(value))
    return params


def encode_scenario(values):
    scenario = {
        "version": SCENARIO_VERSION,
        "parameters": validated_parameter_values(values),
    }
    return json.dumps(scenario, indent=2) + "\n"


def decode_scenario(text):
    scenario = json.loads(text)
    if not isinstance(scenario, dict) or type(scenario.get("version")) is not int:
        raise ValueError("This file is not an Apogee scenario.")
    if scenario["version"] != SCENARIO_VERSION:
        raise ValueError("This scenario file version is not supported.")
    return validated_parameter_values(scenario.get("parameters"))
