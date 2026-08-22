"""Compatibility entry point for the retired Matplotlib result plotter.

APOGEE now sends simulation and analysis results through the single Rerun
visualization pipeline. New code should import ``show_result`` from
``visualization`` directly.
"""

from visualization import show_result


plot_result = show_result

__all__ = ["plot_result"]
