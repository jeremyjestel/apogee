from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import apogee
from analysis.catalog import (
    CURVE,
    GRID_SERIES,
    METRIC_TABLE,
    build_analysis_catalog,
)


def _radar_result():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.2)
    apogee.set_parameter(params, "blue_radar.radar.bandwidth_hz", 10_000.0)
    apogee.set_parameter(params, "blue_radar.radar.pulse_width_us", 100.0)
    apogee.set_parameter(params, "blue_radar.radar.pri_us", 1_000.0)
    return apogee.run_sim(params)


def _curve(key, *, order=0, group=""):
    axis = apogee.Axis()
    axis.key = "range_km"
    axis.name = "Range"
    axis.unit = "km"
    axis.kind = "continuous"
    axis.values = [1.0]

    curve = apogee.Curve1D()
    curve.system = "radar"
    curve.key = key
    curve.name = key.replace("_", " ").title()
    curve.x_axis = axis
    curve.value_unit = "dB"
    curve.values = [1.0]
    presentation = apogee.Presentation()
    presentation.order = order
    presentation.group = group
    curve.presentation = presentation
    return curve


def test_analysis_catalog_normalizes_the_three_supported_shapes():
    catalog = build_analysis_catalog(_radar_result())
    radar = next(entity for entity in catalog.entities if entity.key == "blue_radar")
    products = [product for product in catalog.products if product.entity == radar]

    assert [(product.kind, product.key) for product in products] == [
        (CURVE, "snr"),
        (GRID_SERIES, "range_doppler_noisy"),
        (METRIC_TABLE, "state"),
    ]
    curve, grid, table = products
    assert curve.values.ndim == 1
    assert grid.values.shape == (2, 27, 16)
    assert [axis.key for axis in grid.axes] == [
        "simulation_time",
        "pulse_index",
        "range_km",
    ]
    metrics = {metric.key: metric for metric in table.metrics}
    assert len(metrics["target_range"].values) == 2
    assert len(metrics["pulse_width"].values) == 1
    assert not grid.values.flags.writeable
    assert all(not axis.values.flags.writeable for axis in grid.axes)


def test_analysis_order_and_group_are_generic_presentation_metadata():
    result = apogee.Result()
    result.curves = [
        _curve("automatic"),
        _curve("second", order=20, group="Detection"),
        _curve("first", order=10, group="Detection"),
    ]

    products = build_analysis_catalog(result).products
    assert [product.key for product in products] == ["first", "second", "automatic"]
    assert [product.group for product in products] == ["Detection", "Detection", ""]


def test_analysis_catalog_rejects_duplicate_product_identity():
    result = apogee.Result()
    result.curves = [_curve("duplicate"), _curve("duplicate")]
    with pytest.raises(ValueError, match="identities must be unique"):
        build_analysis_catalog(result)


def test_offscreen_analysis_workspace_and_time_controls():
    source_root = Path(__file__).resolve().parents[1] / "src" / "python"
    script = """
from add_build_to_path import add_apogee_build_to_path
add_apogee_build_to_path()
import apogee
from PySide6.QtWidgets import QApplication
from analysis import AnalysisWorkspace, build_analysis_catalog
from analysis.renderers import GRID_SERIES, METRIC_TABLE, RENDERERS

params = apogee.Params()
apogee.set_parameter(params, 'simulation.duration_s', 0.2)
apogee.set_parameter(params, 'blue_radar.radar.bandwidth_hz', 10000.0)
apogee.set_parameter(params, 'blue_radar.radar.pulse_width_us', 100.0)
apogee.set_parameter(params, 'blue_radar.radar.pri_us', 1000.0)
catalog = build_analysis_catalog(apogee.run_sim(params))
app = QApplication([])
workspace = AnalysisWorkspace(catalog)
workspace.show()
for product in catalog.products:
    widget = RENDERERS[product.kind](product)
    widget.show()
    control = getattr(widget, 'time_control', None)
    if control is not None and control.slider.maximum() > 0:
        control.slider.setValue(control.slider.maximum())
    app.processEvents()
    widget.close()
workspace.close()
app.processEvents()
"""
    environment = dict(**__import__("os").environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=source_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
