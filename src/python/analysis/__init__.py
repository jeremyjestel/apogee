"""Completed-result analysis for the unified PySide application."""

from .catalog import AnalysisCatalog, AnalysisProduct, build_analysis_catalog

__all__ = [
    "AnalysisCatalog",
    "AnalysisProduct",
    "AnalysisWorkspace",
    "build_analysis_catalog",
]


def __getattr__(name):
    # Catalog consumers do not need Qt or a Matplotlib GUI backend.
    if name == "AnalysisWorkspace":
        from .viewer import AnalysisWorkspace

        return AnalysisWorkspace
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
