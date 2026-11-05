"""Scenario dialog location and ownership of the launched Rerun viewers."""

import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import parameter_window
from visualization import rerun_adapter


def test_load_dialog_starts_in_project_scenarios(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = parameter_window.ParameterWindow()
    dialog = Mock(return_value=("", "JSON"))
    monkeypatch.setattr(parameter_window.QFileDialog, "getOpenFileName", dialog)
    window.load_scenario()
    assert dialog.call_args.args[2] == str(parameter_window.SCENARIO_DIRECTORY)
    assert parameter_window.SCENARIO_DIRECTORY.is_dir()
    window.close()
    app.processEvents()


def test_close_parameters_closes_all_owned_viewers_and_any_late_spawn():
    app = QApplication.instance() or QApplication([])
    window = parameter_window.ParameterWindow()
    viewers = [Mock(), Mock()]
    for viewer in viewers:
        window._register_viewer(viewer)
    window.close()
    for viewer in viewers:
        viewer.close.assert_called_once()
    assert window._rerun_viewers == []
    late_viewer = Mock()
    window._register_viewer(late_viewer)
    late_viewer.close.assert_called_once()
    assert window._rerun_viewers == []
    app.processEvents()


def test_worker_registers_viewer_before_logging_can_finish(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = parameter_window.ParameterWindow()
    result, viewer = object(), Mock()
    monkeypatch.setattr(parameter_window.apogee, "run_sim", lambda params: result)
    monkeypatch.setattr(parameter_window, "build_analysis_catalog", lambda result: object())

    def spawn(result, *, on_spawn):
        on_spawn(viewer)
        assert viewer in window._rerun_viewers
        window.close()
        viewer.close.assert_called_once()

    monkeypatch.setattr(parameter_window, "view_rerun", spawn)
    window._run_worker(object())
    assert window._cancel_run.is_set()
    app.processEvents()


def test_logging_failure_closes_launched_viewer(monkeypatch):
    viewer, recording = Mock(), Mock()
    monkeypatch.setattr(rerun_adapter.ViewerClient, "spawn", Mock(return_value=viewer))
    monkeypatch.setattr(rerun_adapter.rr, "RecordingStream", Mock(return_value=recording))
    monkeypatch.setattr(rerun_adapter.rr, "connect_grpc", Mock())
    monkeypatch.setattr(rerun_adapter, "_log_result", Mock(side_effect=RuntimeError("Logging failed")))
    import pytest
    with pytest.raises(RuntimeError, match="Logging failed"):
        rerun_adapter.view_rerun(object())
    viewer.close.assert_called_once()
    recording.disconnect.assert_called_once()
