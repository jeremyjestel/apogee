from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import threading

import apogee
from PySide6.QtCore import QIODevice, QSaveFile, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from analysis import AnalysisWorkspace, build_analysis_catalog
from visualization import view_rerun


# C++ remains the source of truth for parameter names, units, paths, and defaults.
PARAMETER_SPECS = apogee.parameter_specs()


def default_parameter_values():
    params = apogee.Params()
    return {
        spec.path: str(apogee.get_parameter(params, spec.path))
        for spec in PARAMETER_SPECS
    }


def create_params_from_text(values):
    params = apogee.Params()
    for spec in PARAMETER_SPECS:
        apogee.set_parameter(params, spec.path, float(values[spec.path]))
    return params


def _validated_scenario_values(values):
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
            details.append("Unknown parameters: " + ", ".join(sorted(unknown)))
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


def _parameter_groups():
    groups = {}
    for spec in PARAMETER_SPECS:
        groups.setdefault(spec.group, []).append(spec)
    return groups.items()


class ParameterWindow(QMainWindow):
    """One application shell for configuration and post-run analysis."""

    _run_finished = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = {}
        self._run_thread = None
        self._cancel_run = threading.Event()
        self._run_finished.connect(self._simulation_finished)

        self.setWindowTitle("Apogee")
        self.resize(1280, 820)
        self.setMinimumSize(720, 560)

        self.tabs = QTabWidget()
        self._parameter_tab = self._build_parameter_tab()
        self._analysis_tab = self._build_analysis_tab()
        self.tabs.addTab(self._parameter_tab, "Parameters")
        self._analysis_tab_index = self.tabs.addTab(
            self._analysis_tab,
            "Analysis",
        )
        self.setCentralWidget(self.tabs)
        self._apply_theme()

    def _build_parameter_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        defaults = default_parameter_values()
        for group_name, specs in _parameter_groups():
            group = QGroupBox(group_name)
            grid = QGridLayout(group)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(2, 1)
            grid.addWidget(QLabel("Parameter"), 0, 0)
            grid.addWidget(QLabel("Unit"), 0, 1)
            grid.addWidget(QLabel("Value for next run"), 0, 2)

            for row, spec in enumerate(specs, start=1):
                grid.addWidget(QLabel(spec.name), row, 0)
                unit = QLabel(spec.unit or "—")
                unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(unit, row, 1)
                entry = QLineEdit(defaults[spec.path])
                entry.textChanged.connect(self._parameters_changed)
                grid.addWidget(entry, row, 2)
                self.entries[spec.path] = entry

            form_layout.addWidget(group)

        form_layout.addStretch(1)
        scroll.setWidget(form)
        page_layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        self.status = QLabel("Ready")
        footer.addWidget(self.status, 1)
        self.save_button = QPushButton("Save Scenario")
        self.save_button.clicked.connect(self.save_scenario)
        footer.addWidget(self.save_button)
        self.load_button = QPushButton("Load Scenario")
        self.load_button.clicked.connect(self.load_scenario)
        footer.addWidget(self.load_button)
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        footer.addWidget(self.run_button)
        page_layout.addLayout(footer)
        return page

    def _build_analysis_tab(self):
        page = QWidget()
        self._analysis_layout = QVBoxLayout(page)
        self._analysis_layout.setContentsMargins(0, 0, 0, 0)
        self._analysis_widget = QLabel(
            "Run the simulation to populate analysis products."
        )
        self._analysis_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._analysis_layout.addWidget(self._analysis_widget)
        return page

    def _apply_theme(self):
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #f4f6f8; color: #18212b; }"
            "QGroupBox { background: #ffffff; border: 1px solid #cbd3df; "
            "border-radius: 4px; margin-top: 12px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; color: #18212b; font-weight: 600; }"
            "QLineEdit { background: #ffffff; color: #18212b; "
            "border: 1px solid #aeb8c6; border-radius: 3px; padding: 5px; }"
            "QLineEdit:focus { border-color: #286eff; }"
            "QPushButton { background: #286eff; color: #ffffff; border: 0; "
            "border-radius: 4px; padding: 7px 16px; font-weight: 600; }"
            "QPushButton:hover { background: #1858d9; }"
            "QPushButton:disabled { background: #9eabc0; }"
            "QTabWidget::pane { border: 1px solid #cbd3df; }"
            "QTabBar::tab { background: #e8edf4; color: #18212b; "
            "padding: 8px 18px; border: 1px solid #cbd3df; }"
            "QTabBar::tab:selected { background: #ffffff; "
            "border-bottom-color: #ffffff; }"
            "QScrollArea { border: 0; }"
        )

    def _parameters_changed(self):
        if self.status.text().startswith("Loaded scenario: "):
            self.status.setText("Parameters modified")

    def save_scenario(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario", "scenario.json", "Apogee scenarios (*.json)"
        )
        if not filename:
            return

        try:
            values = _validated_scenario_values(
                {path: entry.text() for path, entry in self.entries.items()}
            )
            scenario = (json.dumps({"version": 1, "parameters": values}, indent=2) + "\n")
            data = scenario.encode("utf-8")
            scenario_file = QSaveFile(filename)
            if not scenario_file.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(scenario_file.errorString())
            if scenario_file.write(data) != len(data):
                scenario_file.cancelWriting()
                raise OSError(scenario_file.errorString())
            if not scenario_file.commit():
                raise OSError(scenario_file.errorString())
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Could not save scenario", str(error))
            return

        self.status.setText(f"Saved scenario: {Path(filename).name}")

    def load_scenario(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Scenario", "", "Apogee scenarios (*.json)"
        )
        if not filename:
            return

        try:
            scenario = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
            if not isinstance(scenario, dict) or type(scenario.get("version")) is not int:
                raise ValueError("This file is not an Apogee scenario.")
            if scenario["version"] != 1:
                raise ValueError("This scenario file version is not supported.")
            values = _validated_scenario_values(scenario.get("parameters"))
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Could not load scenario", str(error))
            return

        # Validate the complete file before replacing any editable values.
        for path, value in values.items():
            self.entries[path].setText(value)
        self.tabs.setCurrentWidget(self._parameter_tab)
        self.status.setText(f"Loaded scenario: {Path(filename).name}")

    def run_simulation(self):
        if self._run_thread is not None and self._run_thread.is_alive():
            return

        values = {path: entry.text() for path, entry in self.entries.items()}
        try:
            params = create_params_from_text(values)
        except (KeyError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Invalid parameters", str(error))
            return

        self.run_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.status.setText("Running simulation…")
        self._cancel_run.clear()
        self._run_thread = threading.Thread(
            target=self._run_worker,
            args=(params,),
            name="apogee-simulation",
            daemon=True,
        )
        self._run_thread.start()

    def _run_worker(self, params):
        try:
            result = apogee.run_sim(params)
            if self._cancel_run.is_set():
                return
            catalog = build_analysis_catalog(result)
            if self._cancel_run.is_set():
                return

            rerun_error = None
            try:
                view_rerun(result)
            except Exception as error:
                rerun_error = error
        except Exception as error:
            self._run_finished.emit(None, error)
            return

        self._run_finished.emit(catalog, rerun_error)

    def _simulation_finished(self, catalog, error):
        self._run_thread = None
        self.run_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.load_button.setEnabled(True)

        if catalog is None:
            self.status.setText("Simulation failed")
            QMessageBox.critical(self, "Simulation failed", str(error))
            return

        workspace = AnalysisWorkspace(catalog)
        previous = self._analysis_widget
        self._analysis_layout.replaceWidget(previous, workspace)
        self._analysis_widget = workspace
        previous.deleteLater()
        self.tabs.setCurrentIndex(self._analysis_tab_index)
        self.status.setText("Ready for another run")

        if error is not None:
            QMessageBox.warning(
                self,
                "Rerun unavailable",
                f"Analysis is ready, but the scene viewer could not open:\n{error}",
            )

    def closeEvent(self, event):
        self._cancel_run.set()
        event.accept()


def show_parameter_window(argv=None):
    application = QApplication.instance()
    owns_event_loop = application is None
    if application is None:
        application = QApplication(sys.argv if argv is None else argv)
        application.setApplicationName("Apogee")
        application.setOrganizationName("Apogee")

    window = ParameterWindow()
    window.showMaximized()
    if owns_event_loop:
        return application.exec()
    return window
