"""Lifecycle management for an external Rerun Viewer process."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


SW_MAXIMIZE = 3


def find_rerun_executable(executable: str | Path | None = None) -> Path:
    """Find Rerun beside the active Python environment, then on PATH."""

    if executable is not None:
        requested = Path(executable).expanduser().resolve()
        if requested.is_file():
            return requested
        raise FileNotFoundError(f"The Rerun executable was not found: {requested}")

    environment_root = Path(sys.prefix)
    python_directory = Path(sys.executable).resolve().parent
    if os.name == "nt":
        candidates = (
            environment_root / "Scripts" / "rerun.exe",
            python_directory / "Scripts" / "rerun.exe",
            python_directory / "rerun.exe",
        )
    else:
        candidates = (
            environment_root / "bin" / "rerun",
            python_directory / "rerun",
        )

    for candidate in dict.fromkeys(candidates):
        if candidate.is_file():
            return candidate

    discovered = shutil.which("rerun")
    if discovered:
        return Path(discovered).resolve()

    raise FileNotFoundError(
        "The Rerun executable was not found on PATH or in the active "
        f"Python environment ({environment_root})."
    )


def _maximize_process_window(process_id: int) -> bool:
    """Best-effort maximization of a visible Windows process window."""

    if os.name != "nt":
        return True

    found_window = False
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )

    @callback_type
    def visit_window(window_handle, unused_parameter):
        nonlocal found_window
        window_process_id = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(
            window_handle,
            ctypes.byref(window_process_id),
        )

        if (
            window_process_id.value == process_id
            and ctypes.windll.user32.IsWindowVisible(window_handle)
        ):
            ctypes.windll.user32.ShowWindowAsync(window_handle, SW_MAXIMIZE)
            found_window = True
            return False

        return True

    try:
        ctypes.windll.user32.EnumWindows(visit_window, 0)
    except (AttributeError, OSError):
        return False
    return found_window


class ViewerSession:
    """Own one temporary recording and its external Rerun process."""

    def __init__(
        self,
        *,
        executable: str | Path | None = None,
        maximize_on_windows: bool = True,
    ):
        self._requested_executable = executable
        self._maximize_on_windows = maximize_on_windows
        self._process: subprocess.Popen | None = None
        self._recording_path: Path | None = None
        self._window_maximized = False

    @property
    def recording_path(self) -> Path | None:
        return self._recording_path

    def start(
        self,
        write_recording: Callable[[Path], object],
        *,
        window_size: tuple[int, int] | None = None,
    ) -> Path:
        """Write a temporary recording and launch a new Viewer for it."""

        if self._process is not None and self._process.poll() is None:
            raise RuntimeError("A Rerun Viewer session is already active.")

        self.cleanup()
        rerun_executable = find_rerun_executable(self._requested_executable)

        temp_file = tempfile.NamedTemporaryFile(
            prefix="apogee_",
            suffix=".rrd",
            delete=False,
        )
        temp_file.close()
        self._recording_path = Path(temp_file.name)

        try:
            write_recording(self._recording_path)
            arguments = [
                str(rerun_executable),
                str(self._recording_path),
                "--renderer=gl",
            ]
            if window_size is not None:
                width, height = window_size
                arguments.append(f"--window-size={width}x{height}")
            arguments.append("--new")

            popen_options = {}
            if os.name == "nt" and self._maximize_on_windows:
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = SW_MAXIMIZE
                popen_options["startupinfo"] = startup_info

            self._process = subprocess.Popen(arguments, **popen_options)
            self._window_maximized = not (
                os.name == "nt" and self._maximize_on_windows
            )
        except Exception:
            self.cleanup()
            raise

        return self._recording_path

    def poll(self) -> int | None:
        """Return the Viewer exit code, maximizing its window while it starts."""

        if self._process is None:
            return 0

        exit_code = self._process.poll()
        if exit_code is None and not self._window_maximized:
            self._window_maximized = _maximize_process_window(self._process.pid)
        return exit_code

    def cleanup(self) -> None:
        """Remove an exited session's temporary recording and reset its state."""

        if self._recording_path is not None:
            self._recording_path.unlink(missing_ok=True)
        self._recording_path = None
        self._process = None
        self._window_maximized = False
