"""Compatibility imports for the Rerun visualization package.

New code should import from ``visualization`` directly.
"""

from visualization import log_result, save_result, show_result


show_in_rerun = show_result

__all__ = ["log_result", "save_result", "show_in_rerun", "show_result"]
