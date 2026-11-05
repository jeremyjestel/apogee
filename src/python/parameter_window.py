from __future__ import annotations

from pathlib import Path
import sys
import threading

import apogee
from PySide6.QtCore import QIODevice, QSaveFile, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from analysis import AnalysisWorkspace, build_analysis_catalog
from scenario import (
    PARAMETER_SPECS,
    ENTITY_TYPES,
    create_params_from_text,
    decode_scenario,
    decode_scenario_definition,
    default_parameter_values,
    encode_scenario,
)
from visualization import view_rerun


SCENARIO_DIRECTORY = Path(__file__).resolve().parents[2] / "scenarios"


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
        self.params = apogee.Params()
        self.entity_cards = {}
        self._next_entity_id = max(entity.id for entity in self.params.entities) + 1
        self._run_thread = None
        self._cancel_run = threading.Event()
        self._viewer_lock = threading.Lock()
        self._rerun_viewers = []
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

        self._form = form
        entity_tools = QHBoxLayout()
        entity_tools.addWidget(QLabel("New entity type:"))
        self.add_entity_type = QComboBox()
        self.add_entity_type.addItems(ENTITY_TYPES)
        entity_tools.addWidget(self.add_entity_type)
        self.add_entity_button = QPushButton("+ Add Entity")
        self.add_entity_button.clicked.connect(
            lambda: self.add_entity(self.add_entity_type.currentText())
        )
        entity_tools.addWidget(self.add_entity_button)
        entity_tools.addStretch(1)
        form_layout.addLayout(entity_tools)

        defaults = default_parameter_values()
        for group_name, specs in _parameter_groups():
            specs = [spec for spec in specs if spec.path.startswith(("simulation.", "radar_analysis."))]
            if not specs:
                continue
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

        self._entity_list = QWidget()
        self._entity_layout = QVBoxLayout(self._entity_list)
        self._entity_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.addWidget(self._entity_list)
        self._rebuild_entities()

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

    def _repair_targets(self):
        entities = self.params.entities
        keys = {entity.key for entity in entities}
        for entity in entities:
            if entity.type not in ("missile", "interceptor"):
                continue
            pursuit = entity.initial_pursuit
            if pursuit is None or pursuit.target_key in keys - {entity.key}:
                continue
            preferred = "satellite" if entity.type == "missile" else "missile"
            candidates = [other for other in entities if other.key != entity.key]
            target = next((other for other in candidates if other.type == preferred), candidates[0])
            self.params.entity(entity.key).initial_pursuit.target_key = target.key

    def _rebuild_entities(self, values=None):
        values = self._entry_values() if values is None else values
        expanded = {key: card.toggle.isChecked() for key, card in self.entity_cards.items()}
        self.entries = {path: entry for path, entry in self.entries.items()
                        if path.startswith(("simulation.", "radar_analysis."))}
        while self._entity_layout.count():
            widget = self._entity_layout.takeAt(0).widget()
            widget.setParent(None)
            widget.deleteLater()
        self.entity_cards = {}
        self._repair_targets()
        defaults = default_parameter_values(self.params)
        specs = apogee.parameter_specs(self.params)
        entities = self.params.entities
        for entity in entities:
            key = entity.key
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            layout = QVBoxLayout(card)
            header = QHBoxLayout()
            card.toggle = QToolButton()
            card.toggle.setText("Parameters")
            card.toggle.setCheckable(True)
            card.toggle.setChecked(expanded.get(key, False))
            card.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            header.addWidget(card.toggle)
            card.name_entry = QLineEdit(entity.display_name)
            card.name_entry.setPlaceholderText("Entity name")
            card.name_entry.textChanged.connect(
                lambda text, key=key: self._set_entity_attribute(key, "display_name", text)
            )
            header.addWidget(card.name_entry, 1)
            header.addWidget(QLabel("Type"))
            card.type_combo = QComboBox()
            card.type_combo.addItems(ENTITY_TYPES)
            card.type_combo.setCurrentText(entity.type)
            card.type_combo.currentTextChanged.connect(
                lambda kind, key=key: self._change_entity_type(key, kind)
            )
            header.addWidget(card.type_combo)
            header.addWidget(QLabel("Team"))
            card.team_combo = QComboBox()
            card.team_combo.setEditable(True)
            card.team_combo.addItems(("blue", "red", "neutral"))
            card.team_combo.setCurrentText(entity.team)
            card.team_combo.currentTextChanged.connect(
                lambda team, key=key: self._set_entity_attribute(key, "team", team)
            )
            header.addWidget(card.team_combo)
            card.remove_button = QPushButton("−")
            card.remove_button.setToolTip("Remove entity")
            card.remove_button.setEnabled(sum(other.type == entity.type for other in entities) > 1)
            card.remove_button.clicked.connect(lambda _checked=False, key=key: self.remove_entity(key))
            header.addWidget(card.remove_button)
            layout.addLayout(header)
            card.body = QWidget()
            grid = QGridLayout(card.body)
            grid.setColumnStretch(2, 1)
            grid.addWidget(QLabel("Parameter"), 0, 0)
            grid.addWidget(QLabel("Unit"), 0, 1)
            grid.addWidget(QLabel("Value for next run"), 0, 2)
            row = 1
            if entity.type in ("missile", "interceptor"):
                grid.addWidget(QLabel("Target entity"), row, 0)
                card.target_combo = QComboBox()
                for other in entities:
                    if other.key != key:
                        card.target_combo.addItem(f"{other.display_name} [{other.key}]", other.key)
                card.target_combo.setCurrentIndex(
                    card.target_combo.findData(entity.initial_pursuit.target_key)
                )
                card.target_combo.currentIndexChanged.connect(
                    lambda _index, key=key, combo=card.target_combo: self._set_target(key, combo.currentData())
                )
                grid.addWidget(card.target_combo, row, 2)
                row += 1
            for spec in specs:
                if not spec.path.startswith(key + "."):
                    continue
                grid.addWidget(QLabel(spec.name), row, 0)
                grid.addWidget(QLabel(spec.unit or "—"), row, 1)
                entry = QLineEdit(values.get(spec.path, defaults[spec.path]))
                entry.textChanged.connect(self._parameters_changed)
                grid.addWidget(entry, row, 2)
                self.entries[spec.path] = entry
                row += 1
            card.toggle.toggled.connect(lambda checked, card=card: self._toggle_entity(card, checked))
            self._toggle_entity(card, card.toggle.isChecked())
            layout.addWidget(card.body)
            self._entity_layout.addWidget(card)
            self.entity_cards[key] = card

    @staticmethod
    def _toggle_entity(card, expanded):
        card.body.setVisible(expanded)
        card.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def _set_entity_attribute(self, key, attribute, value):
        setattr(self.params.entity(key), attribute, value)
        self._parameters_changed()

    def _set_target(self, key, target):
        self.params.entity(key).initial_pursuit.target_key = target
        self._parameters_changed()

    def add_entity(self, kind=None):
        kind = self.add_entity_type.currentText() if kind is None else kind
        keys = {entity.key for entity in self.params.entities}
        while f"{kind}_{self._next_entity_id}" in keys:
            self._next_entity_id += 1
        key = f"{kind}_{self._next_entity_id}"
        entity = apogee.make_entity_definition(kind, key, self._next_entity_id)
        entity.display_name = f"{kind.title()} {entity.id}"
        self._next_entity_id += 1
        self.params.entities = [*self.params.entities, entity]
        self._rebuild_entities()
        self.entity_cards[key].toggle.setChecked(True)
        self.status.setText(f"Added {entity.display_name}")
        return key

    def remove_entity(self, key):
        entity = self.params.entity(key)
        if sum(other.type == entity.type for other in self.params.entities) == 1:
            self.status.setText(f"Keep at least one {entity.type} in the scenario")
            return False
        name = entity.display_name
        self.params.entities = [other for other in self.params.entities if other.key != key]
        self._rebuild_entities()
        self.status.setText(f"Removed {name}")
        return True

    def _change_entity_type(self, key, kind):
        entity = self.params.entity(key)
        if sum(other.type == entity.type for other in self.params.entities) == 1:
            combo = self.entity_cards[key].type_combo
            combo.blockSignals(True)
            combo.setCurrentText(entity.type)
            combo.blockSignals(False)
            self.status.setText(f"Keep at least one {entity.type} in the scenario")
            return
        replacement = apogee.make_entity_definition(kind, key, entity.id)
        replacement.display_name, replacement.team = entity.display_name, entity.team
        self.params.entities = [replacement if other.key == key else other for other in self.params.entities]
        self._rebuild_entities()
        self.status.setText("Entity type changed")

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
        if self.status.text().startswith(("Loaded scenario: ", "Saved scenario: ")):
            self.status.setText("Parameters modified")

    def _entry_values(self):
        return {path: entry.text() for path, entry in self.entries.items()}

    def _set_running(self, running):
        self._form.setEnabled(not running)
        for button in (self.run_button, self.save_button, self.load_button):
            button.setEnabled(not running)

    def save_scenario(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario", "scenario.json", "Apogee scenarios (*.json)"
        )
        if not filename:
            return

        try:
            data = encode_scenario(self._entry_values(), self.params).encode("utf-8")
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
            self, "Load Scenario", str(SCENARIO_DIRECTORY), "Apogee scenarios (*.json)"
        )
        if not filename:
            return

        try:
            params, values = decode_scenario_definition(Path(filename).read_text(encoding="utf-8-sig"))
        except (OSError, KeyError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Could not load scenario", str(error))
            return

        # Validate the complete file before replacing any editable values.
        self.params = params
        self._next_entity_id = max(entity.id for entity in params.entities) + 1
        self._rebuild_entities(values)
        for path, value in values.items():
            self.entries[path].setText(value)
        self.tabs.setCurrentWidget(self._parameter_tab)
        self.status.setText(f"Loaded scenario: {Path(filename).name}")

    def run_simulation(self):
        # A finished worker can still have its completion queued on the GUI thread.
        if self._run_thread is not None:
            return

        try:
            params = create_params_from_text(self._entry_values(), self.params)
        except (KeyError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Invalid parameters", str(error))
            return

        self._set_running(True)
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
                view_rerun(result, on_spawn=self._register_viewer)
            except Exception as error:
                rerun_error = error
        except Exception as error:
            if not self._cancel_run.is_set():
                self._run_finished.emit(None, error)
            return

        if not self._cancel_run.is_set():
            self._run_finished.emit(catalog, rerun_error)

    def _simulation_finished(self, catalog, error):
        self._run_thread = None
        # The window may close after the worker has emitted its queued signal.
        if self._cancel_run.is_set():
            return
        self._set_running(False)

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

    def _register_viewer(self, viewer):
        with self._viewer_lock:
            if not self._cancel_run.is_set():
                self._rerun_viewers.append(viewer)
                return
        # Closing the parameters window can race a viewer starting in the worker.
        viewer.close()

    def closeEvent(self, event):
        self._cancel_run.set()
        with self._viewer_lock:
            viewers, self._rerun_viewers = self._rerun_viewers, []
        for viewer in viewers:
            viewer.close()
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
