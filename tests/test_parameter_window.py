import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from analysis.catalog import AnalysisCatalog
import parameter_window
from parameter_window import PARAMETER_SPECS, ParameterWindow


def _application():
    return QApplication.instance() or QApplication([])


def test_parameter_window_generates_the_qt_form_and_analysis_tab():
    application = _application()
    window = ParameterWindow()

    assert len(window.entries) == len(PARAMETER_SPECS)
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Parameters",
        "Analysis",
    ]
    assert window.status.text() == "Ready"

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

    window.close()
    application.processEvents()
