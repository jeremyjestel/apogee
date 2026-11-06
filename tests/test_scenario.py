import json
from pathlib import Path
import subprocess
import sys

import pytest

import apogee
from scenario import (
    create_params_from_text, decode_scenario, decode_scenario_definition,
    default_parameter_values, encode_scenario,
)


def test_scenario_helpers_can_be_used_without_loading_the_ui():
    python_source = Path(__file__).resolve().parents[1] / "src" / "python"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from add_build_to_path import add_apogee_build_to_path; "
            "add_apogee_build_to_path(); "
            "from scenario import default_parameter_values; "
            "assert default_parameter_values(); "
            "assert 'PySide6' not in sys.modules; "
            "assert 'rerun' not in sys.modules",
            str(python_source),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_scenario_format_round_trip_preserves_numeric_text():
    values = default_parameter_values()
    values[next(iter(values))] = " 1.2500e1 "

    assert decode_scenario(encode_scenario(values)) == values


def test_scenario_uses_default_targets_when_not_overridden():
    original = apogee.Params()
    saved = json.loads(encode_scenario(default_parameter_values(original), original))
    for entity in saved["entities"]:
        entity.pop("target_key", None)

    params, _ = decode_scenario_definition(json.dumps(saved))

    assert params.entity("red_missile").initial_pursuit.target_key == "blue_satellite"
    assert params.entity("blue_interceptor").initial_pursuit.target_key == "red_missile"


@pytest.mark.parametrize("version", [1, 2])
def test_guidance_gain_round_trip_and_older_scenario_default(version):
    original = apogee.Params()
    values = default_parameter_values(original)
    paths = {path for path in values if path.endswith(".guidance_gain")}
    assert paths == {"red_missile.initial_pursuit.guidance_gain",
                     "blue_interceptor.initial_pursuit.guidance_gain"}
    values["red_missile.initial_pursuit.guidance_gain"] = " 0.7500 "
    encoded = encode_scenario(values, original if version == 2 else None)
    definition, restored = decode_scenario_definition(encoded)
    params = create_params_from_text(restored, definition)
    assert restored == values
    assert params.entity("red_missile").initial_pursuit.guidance_gain == 0.75
    assert params.entity("blue_interceptor").initial_pursuit.guidance_gain == 0.5

    legacy = json.loads(encoded)
    for path in paths:
        legacy["parameters"].pop(path)
    _, restored = decode_scenario_definition(json.dumps(legacy))
    assert all(restored[path] == "0.5" for path in paths)


@pytest.mark.parametrize("version", [True, False, 1.0, "1", None])
def test_scenario_format_requires_an_integer_version(version):
    text = json.dumps({"version": version, "parameters": default_parameter_values()})

    with pytest.raises(ValueError, match="not an Apogee scenario"):
        decode_scenario(text)


def test_radar_processing_settings_round_trip_with_native_types():
    values = default_parameter_values()
    values["blue_radar.radar.pulse_num"] = " 3.2e1 "
    values["blue_radar.radar.range_window"] = "hamming"
    values["blue_radar.radar.doppler_window"] = "hann"

    restored = decode_scenario(encode_scenario(values))
    params = create_params_from_text(restored)

    assert restored == values
    assert apogee.get_parameter(params, "blue_radar.radar.pulse_num") == 32
    assert type(apogee.get_parameter(params, "blue_radar.radar.pulse_num")) is int
    assert params.entity("blue_radar").radar.range_window == "hamming"
    assert params.entity("blue_radar").radar.doppler_window == "hann"


@pytest.mark.parametrize("missing", [("pulse_num",), ("range_window", "doppler_window"),
                                   ("pulse_num", "range_window", "doppler_window")])
def test_loading_earlier_v1_scenario_defaults_only_missing_processing_settings(missing):
    values = default_parameter_values()
    values["blue_radar.radar.power_dbw"] = " 42.00 "
    values["blue_radar.radar.range_window"] = "hamming"
    legacy_values = values.copy()
    defaults = default_parameter_values()
    for field in missing:
        path = "blue_radar.radar." + field
        legacy_values.pop(path)
        values[path] = defaults[path]

    restored = decode_scenario(json.dumps({"version": 1, "parameters": legacy_values}))

    assert restored == values
    assert create_params_from_text(restored).entity("blue_radar").radar.pulse_num == 16


@pytest.mark.parametrize("value", [3, 32])
def test_parameter_binding_preserves_integer_type(value):
    params = apogee.Params()

    apogee.set_parameter(params, "blue_radar.radar.pulse_num", value)

    stored = apogee.get_parameter(params, "blue_radar.radar.pulse_num")
    assert type(stored) is int
    assert stored == value


def test_checked_in_scenario_contains_current_processing_defaults():
    path = Path(__file__).resolve().parents[1] / "scenarios" / "default_scenario.json"

    params = create_params_from_text(decode_scenario(path.read_text(encoding="utf-8")))

    assert params.entity("blue_radar").radar.pulse_num == 16
    assert params.entity("blue_radar").radar.range_window == "rectangular"
    assert params.entity("blue_radar").radar.doppler_window == "rectangular"
