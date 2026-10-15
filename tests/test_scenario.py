import json
from pathlib import Path
import subprocess
import sys

import pytest

from scenario import decode_scenario, default_parameter_values, encode_scenario


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


@pytest.mark.parametrize("version", [True, False, 1.0, "1", None])
def test_scenario_format_requires_an_integer_version(version):
    text = json.dumps({"version": version, "parameters": default_parameter_values()})

    with pytest.raises(ValueError, match="not an Apogee scenario"):
        decode_scenario(text)
