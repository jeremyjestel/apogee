import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from analysis.catalog import AnalysisCatalog
import parameter_window
from parameter_window import PARAMETER_SPECS, ParameterWindow, create_params_from_text


def _application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scenario_window(monkeypatch):
    application = _application()
    window = ParameterWindow()
    errors = []
    monkeypatch.setattr(
        parameter_window.QMessageBox,
        "critical",
        lambda parent, title, message: errors.append((title, message)),
    )
    yield window, errors
    window.close()
    application.processEvents()


def _entry_values(window):
    return {path: entry.text() for path, entry in window.entries.items()}


def _select_file(monkeypatch, dialog, path):
    monkeypatch.setattr(
        parameter_window.QFileDialog,
        dialog,
        lambda *args, **kwargs: (str(path), "JSON files (*.json)"),
    )


def test_parameter_window_generates_the_qt_form_and_analysis_tab():
    application = _application()
    window = ParameterWindow()

    assert len(window.entries) == len(PARAMETER_SPECS)
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Parameters",
        "Analysis",
    ]
    assert window.status.text() == "Ready"
    assert window.save_button.text() == "Save Scenario"
    assert window.load_button.text() == "Load Scenario"

    window.close()
    application.processEvents()


def test_completed_run_embeds_analysis_and_opens_rerun(monkeypatch):
    application = _application()
    window = ParameterWindow()
    result = object()
    catalog = AnalysisCatalog(entities=(), products=())
    viewed = []

    monkeypatch.setattr(parameter_window.apogee, "run_sim", lambda params: result)
    monkeypatch.setattr(
        parameter_window,
        "build_analysis_catalog",
        lambda value: catalog,
    )
    monkeypatch.setattr(parameter_window, "view_rerun", viewed.append)

    window._run_worker(object())
    application.processEvents()

    assert viewed == [result]
    assert window.tabs.currentIndex() == window._analysis_tab_index
    assert window.status.text() == "Ready for another run"
    assert window.run_button.isEnabled()
    assert window.save_button.isEnabled()
    assert window.load_button.isEnabled()

    window.close()
    application.processEvents()


def test_scenario_save_load_preserves_text_and_builds_parameters(
    scenario_window, monkeypatch, tmp_path
):
    window, errors = scenario_window
    paths = list(window.entries)
    window.entries[paths[0]].setText("1.2500e1")
    window.entries[paths[1]].setText(" 2.50 ")
    saved_values = _entry_values(window)
    scenario_path = tmp_path / "scenario.json"
    _select_file(monkeypatch, "getSaveFileName", scenario_path)

    window.save_button.click()

    assert json.loads(scenario_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "parameters": saved_values,
    }
    assert _entry_values(window) == saved_values

    for entry in window.entries.values():
        entry.setText("99")
    window.tabs.setCurrentIndex(window._analysis_tab_index)
    _select_file(monkeypatch, "getOpenFileName", scenario_path)

    window.load_button.click()

    assert _entry_values(window) == saved_values
    assert window.tabs.currentWidget() is window._parameter_tab
    assert window.status.text() == "Loaded scenario: scenario.json"
    assert window._run_thread is None
    params = create_params_from_text(_entry_values(window))
    for path, value in saved_values.items():
        assert parameter_window.apogee.get_parameter(params, path) == float(value)
    window.entries[paths[0]].setText("42")
    assert window.status.text() == "Parameters modified"
    window.load_button.click()
    assert _entry_values(window) == saved_values
    assert window.status.text() == "Loaded scenario: scenario.json"
    assert errors == []


def test_editing_a_saved_scenario_updates_status(scenario_window, monkeypatch, tmp_path):
    window, errors = scenario_window
    _select_file(monkeypatch, "getSaveFileName", tmp_path / "scenario.json")

    window.save_scenario()
    assert window.status.text() == "Saved scenario: scenario.json"

    next(iter(window.entries.values())).setText("42")

    assert window.status.text() == "Parameters modified"
    assert errors == []


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_scenario_load_accepts_numeric_values(
    scenario_window, monkeypatch, tmp_path, encoding
):
    window, errors = scenario_window
    values = _entry_values(window)
    path = next(iter(values))
    values[path] = 12.5
    scenario_path = tmp_path / "numeric.json"
    scenario_path.write_text(
        json.dumps({"version": 1, "parameters": values}), encoding=encoding
    )
    _select_file(monkeypatch, "getOpenFileName", scenario_path)

    window.load_scenario()

    assert window.entries[path].text() == "12.5"
    params = create_params_from_text(_entry_values(window))
    assert parameter_window.apogee.get_parameter(params, path) == 12.5
    assert errors == []


@pytest.mark.parametrize("key_change", ["missing", "unknown"])
def test_scenario_load_rejects_incomplete_parameter_sets_without_changes(
    scenario_window, monkeypatch, tmp_path, key_change
):
    window, errors = scenario_window
    original_values = _entry_values(window)
    values = dict.fromkeys(original_values, "123")
    if key_change == "missing":
        values.pop(next(iter(values)))
    else:
        values["unknown.parameter"] = "123"
    scenario_path = tmp_path / "invalid-keys.json"
    scenario_path.write_text(
        json.dumps({"version": 1, "parameters": values}), encoding="utf-8"
    )
    _select_file(monkeypatch, "getOpenFileName", scenario_path)

    window.load_scenario()

    assert _entry_values(window) == original_values
    assert len(errors) == 1


@pytest.mark.parametrize(
    "invalid_value", [True, None, [], {}, "not a number", "nan", "inf", float("inf")]
)
def test_scenario_load_rejects_invalid_values_without_partial_changes(
    scenario_window, monkeypatch, tmp_path, invalid_value
):
    window, errors = scenario_window
    original_values = _entry_values(window)
    values = dict.fromkeys(original_values, "123")
    values[list(values)[-1]] = invalid_value
    scenario_path = tmp_path / "invalid-value.json"
    scenario_path.write_text(
        json.dumps({"version": 1, "parameters": values}), encoding="utf-8"
    )
    _select_file(monkeypatch, "getOpenFileName", scenario_path)

    window.load_scenario()

    assert _entry_values(window) == original_values
    assert len(errors) == 1


@pytest.mark.parametrize("file_kind", ["malformed", "unsupported-version", "unreadable"])
def test_scenario_load_reports_file_errors_without_changes(
    scenario_window, monkeypatch, tmp_path, file_kind
):
    window, errors = scenario_window
    original_values = _entry_values(window)
    scenario_path = tmp_path / "invalid-file.json"
    if file_kind == "malformed":
        scenario_path.write_text("{", encoding="utf-8")
    elif file_kind == "unsupported-version":
        scenario_path.write_text(
            json.dumps({"version": 2, "parameters": original_values}),
            encoding="utf-8",
        )
    _select_file(monkeypatch, "getOpenFileName", scenario_path)

    window.load_scenario()

    assert _entry_values(window) == original_values
    assert len(errors) == 1


@pytest.mark.parametrize(
    ("method", "dialog"),
    [("save_scenario", "getSaveFileName"), ("load_scenario", "getOpenFileName")],
)
def test_canceling_scenario_dialog_leaves_parameters_unchanged(
    scenario_window, monkeypatch, method, dialog
):
    window, errors = scenario_window
    original_values = _entry_values(window)
    _select_file(monkeypatch, dialog, "")

    getattr(window, method)()

    assert _entry_values(window) == original_values
    assert errors == []


def test_scenario_save_reports_write_error_without_changes(
    scenario_window, monkeypatch, tmp_path
):
    window, errors = scenario_window
    original_values = _entry_values(window)
    _select_file(monkeypatch, "getSaveFileName", tmp_path)

    window.save_scenario()

    assert _entry_values(window) == original_values
    assert len(errors) == 1


def test_scenario_save_rejects_invalid_values_before_overwriting_file(
    scenario_window, monkeypatch, tmp_path
):
    window, errors = scenario_window
    next(iter(window.entries.values())).setText("not a number")
    original_values = _entry_values(window)
    scenario_path = tmp_path / "existing.json"
    scenario_path.write_text("previous scenario", encoding="utf-8")
    _select_file(monkeypatch, "getSaveFileName", scenario_path)

    window.save_scenario()

    assert scenario_path.read_text(encoding="utf-8") == "previous scenario"
    assert _entry_values(window) == original_values
    assert len(errors) == 1


def test_scenario_buttons_are_disabled_during_run_and_reenabled_after_failure(
    scenario_window, monkeypatch
):
    window, errors = scenario_window

    class PendingThread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(parameter_window.threading, "Thread", PendingThread)

    window.run_simulation()

    assert not window.run_button.isEnabled()
    assert not window.save_button.isEnabled()
    assert not window.load_button.isEnabled()

    window._simulation_finished(None, RuntimeError("Simulation error"))

    assert window.run_button.isEnabled()
    assert window.save_button.isEnabled()
    assert window.load_button.isEnabled()
    assert len(errors) == 1


@pytest.mark.parametrize("invalid_value", ["not numeric", "nan", "inf", "-inf", "1e5000"])
def test_invalid_run_does_not_start_a_worker(scenario_window, monkeypatch, invalid_value):
    window, errors = scenario_window
    path = next(iter(window.entries))
    window.entries[path].setText(invalid_value)

    def unexpected_thread(**kwargs):
        pytest.fail("Invalid parameters must not start a simulation thread")

    monkeypatch.setattr(parameter_window.threading, "Thread", unexpected_thread)

    window.run_simulation()

    assert window._run_thread is None
    assert window.run_button.isEnabled()
    assert window.save_button.isEnabled()
    assert window.load_button.isEnabled()
    assert errors[0][0] == "Invalid parameters"
    assert path in errors[0][1]


def test_run_waits_for_completion_handler_before_starting_another_worker(
    scenario_window, monkeypatch
):
    window, errors = scenario_window
    starts = []

    class PendingCompletion:
        def __init__(self, **kwargs):
            pass

        def start(self):
            starts.append(self)

        def is_alive(self):
            return False

    monkeypatch.setattr(parameter_window.threading, "Thread", PendingCompletion)

    window.run_simulation()
    window.run_simulation()

    assert len(starts) == 1
    assert errors == []


@pytest.mark.parametrize("catalog", [None, AnalysisCatalog(entities=(), products=())])
def test_queued_completion_after_close_does_not_change_ui(scenario_window, catalog):
    window, errors = scenario_window
    original_widget = window._analysis_widget
    window.close()

    window._simulation_finished(catalog, RuntimeError("Late error"))

    assert window._analysis_widget is original_widget
    assert window.status.text() == "Ready"
    assert errors == []


def test_worker_failure_after_close_does_not_report_an_error(scenario_window, monkeypatch):
    window, errors = scenario_window

    def failed_run(params):
        raise RuntimeError("Worker stopped after close")

    monkeypatch.setattr(parameter_window.apogee, "run_sim", failed_run)
    window.close()

    window._run_worker(object())
    _application().processEvents()

    assert window.status.text() == "Ready"
    assert errors == []


@pytest.mark.parametrize("operation", ["get_parameter", "set_parameter"])
def test_parameter_path_lookup_rejects_unknown_paths(operation):
    params = parameter_window.apogee.Params()
    arguments = (params, "missing.parameter")
    if operation == "set_parameter":
        arguments += (1.0,)

    with pytest.raises(ValueError, match="Unknown parameter path: missing.parameter"):
        getattr(parameter_window.apogee, operation)(*arguments)
