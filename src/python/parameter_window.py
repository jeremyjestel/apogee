import ctypes
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import apogee

from visualization import save_result


SW_MAXIMIZE = 3


def _maximize_process_window(process_id):
    # Find the visible top-level window created by Rerun's process.
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

    ctypes.windll.user32.EnumWindows(visit_window, 0)
    return found_window


# Let C++ remain the single source of truth for parameter names, units, and paths.
PARAMETER_SPECS = apogee.parameter_specs()


def default_parameter_values():
    # Read defaults from a fresh scenario so the form mirrors C++ initialization.
    params = apogee.Params()
    return {
        spec.path: str(apogee.get_parameter(params, spec.path))
        for spec in PARAMETER_SPECS
    }


def create_params_from_text(values):
    # Build a fresh scenario and apply every text-box value through the C++ path API.
    params = apogee.Params()
    for spec in PARAMETER_SPECS:
        apogee.set_parameter(params, spec.path, float(values[spec.path]))
    return params


def _parameter_groups():
    # Preserve specification order while collecting fields under their UI headings.
    groups = {}
    for spec in PARAMETER_SPECS:
        groups.setdefault(spec.group, []).append(spec)
    return groups.items()


class ParameterWindow:
    def __init__(self, root):
        self.root = root
        self.entries = {}
        self.viewer_process = None
        self.viewer_maximized = False
        self.recording_path = None

        root.title("Apogee Simulation Parameters")
        root.geometry("720x820")
        root.minsize(560, 500)
        root.after_idle(lambda: root.state("zoomed"))

        self._build_parameter_form()

        footer = ttk.Frame(root, padding=10)
        footer.pack(fill="x")
        footer.columnconfigure(0, weight=1)

        self.status = ttk.Label(footer, text="Ready")
        self.status.grid(row=0, column=0, sticky="w")

        self.run_button = ttk.Button(
            footer,
            text="Run Simulation",
            command=self.run_simulation,
        )
        self.run_button.grid(row=0, column=1)

    def _build_parameter_form(self):
        # Place the generated form inside a canvas so a long parameter list can scroll.
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas, padding=12)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Keep the canvas scroll bounds and embedded form width synchronized as it resizes.
        form_window = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(form_window, width=event.width),
        )
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(-event.delta // 120, "units"),
        )

        form.columnconfigure(0, weight=1)
        form.columnconfigure(2, weight=1)

        ttk.Label(form, text="Parameter").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Unit").grid(row=0, column=1, padx=12)
        ttk.Label(form, text="Value for next run").grid(
            row=0,
            column=2,
            sticky="ew",
        )

        # Generate one labeled entry for every parameter exposed by the binding.
        defaults = default_parameter_values()
        row = 1
        for group_name, specs in _parameter_groups():
            ttk.Separator(form).grid(
                row=row,
                column=0,
                columnspan=3,
                sticky="ew",
                pady=(12, 6),
            )
            row += 1
            ttk.Label(form, text=group_name, font=("Segoe UI", 11, "bold")).grid(
                row=row,
                column=0,
                columnspan=3,
                sticky="w",
                pady=(0, 5),
            )
            row += 1

            for spec in specs:
                ttk.Label(form, text=spec.name).grid(
                    row=row,
                    column=0,
                    sticky="w",
                    pady=2,
                )
                ttk.Label(form, text=spec.unit).grid(row=row, column=1, padx=12)

                value = tk.StringVar(value=defaults[spec.path])
                ttk.Entry(form, textvariable=value).grid(
                    row=row,
                    column=2,
                    sticky="ew",
                    pady=2,
                )
                self.entries[spec.path] = value
                row += 1

    def run_simulation(self):
        # Disable repeat submissions while this run is being prepared and displayed.
        self.run_button.configure(state="disabled")
        self.status.configure(text="Running simulation...")
        self.root.update_idletasks()

        try:
            # Convert the current form into a fresh C++ scenario and run it synchronously.
            values = {path: entry.get() for path, entry in self.entries.items()}
            params = create_params_from_text(values)
            result = apogee.run_sim(params)

            # Save the recording to a unique file that the separate viewer process can open.
            temp_file = tempfile.NamedTemporaryFile(
                prefix="apogee_",
                suffix=".rrd",
                delete=False,
            )
            temp_file.close()
            self.recording_path = Path(temp_file.name)
            save_result(result, self.recording_path)

            # Launch the Rerun executable belonging to the active Python environment.
            rerun_executable = Path(sys.executable).parent / "Scripts" / "rerun.exe"
            if not rerun_executable.is_file():
                raise FileNotFoundError(
                    "The Rerun executable was not found in the active environment."
                )

            # Ask Windows to open the external Rerun viewer as a maximized window.
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = SW_MAXIMIZE
            viewer_size = (
                f"{self.root.winfo_screenwidth()}x"
                f"{self.root.winfo_screenheight()}"
            )
            self.viewer_process = subprocess.Popen(
                [
                    str(rerun_executable),
                    str(self.recording_path),
                    "--renderer=gl",
                    f"--window-size={viewer_size}",
                    "--new",
                ],
                startupinfo=startup_info,
            )
        except Exception as error:
            self._restore_after_run()
            messagebox.showerror("Simulation failed", str(error))
            return

        # Hide this window while Rerun is open, then poll without blocking Tk's event loop.
        self.root.withdraw()
        self.root.after(250, self._wait_for_viewer)

    def _wait_for_viewer(self):
        # Reschedule the check until the external viewer process has exited.
        if self.viewer_process.poll() is None:
            if not self.viewer_maximized:
                self.viewer_maximized = _maximize_process_window(
                    self.viewer_process.pid
                )
            self.root.after(250, self._wait_for_viewer)
            return

        # Restore the parameter form for quick changes and another run.
        self._restore_after_run()
        self.root.deiconify()
        self.root.state("zoomed")
        self.root.lift()
        self.root.focus_force()

    def _restore_after_run(self):
        # Delete the temporary recording and reset all per-run UI state.
        if self.recording_path is not None:
            self.recording_path.unlink(missing_ok=True)
        self.recording_path = None
        self.viewer_process = None
        self.viewer_maximized = False
        self.run_button.configure(state="normal")
        self.status.configure(text="Ready for another run")


def show_parameter_window():
    root = tk.Tk()
    ParameterWindow(root)
    root.mainloop()
