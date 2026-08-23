import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import apogee

from visualization import save_result


PARAMETER_SPECS = apogee.parameter_specs()


def _get_parameter(params, path):
    value = params
    for name in path.split("."):
        value = getattr(value, name)
    return value


def _set_parameter(params, path, value):
    names = path.split(".")
    owner = params
    for name in names[:-1]:
        owner = getattr(owner, name)
    setattr(owner, names[-1], value)


def default_parameter_values():
    params = apogee.Params()
    return {
        spec.path: str(_get_parameter(params, spec.path))
        for spec in PARAMETER_SPECS
    }


def create_params_from_text(values):
    params = apogee.Params()
    for spec in PARAMETER_SPECS:
        text = values[spec.path].strip()
        try:
            value = float(text)
        except ValueError as error:
            raise ValueError(f"{spec.group} — {spec.name} must be a number") from error
        _set_parameter(params, spec.path, value)
    return params


def _parameter_groups():
    groups = {}
    for spec in PARAMETER_SPECS:
        groups.setdefault(spec.group, []).append(spec)
    return groups.items()


class ParameterWindow:
    def __init__(self, root):
        self.root = root
        self.entries = {}
        self.viewer_process = None
        self.recording_path = None

        root.title("Apogee Simulation Parameters")
        root.geometry("720x820")
        root.minsize(560, 500)

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
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas, padding=12)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

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
        self.run_button.configure(state="disabled")
        self.status.configure(text="Running simulation...")
        self.root.update_idletasks()

        try:
            values = {path: entry.get() for path, entry in self.entries.items()}
            params = create_params_from_text(values)
            result = apogee.run_sim(params)

            temp_file = tempfile.NamedTemporaryFile(
                prefix="apogee_",
                suffix=".rrd",
                delete=False,
            )
            temp_file.close()
            self.recording_path = Path(temp_file.name)
            save_result(result, self.recording_path)

            rerun_executable = Path(sys.executable).parent / "Scripts" / "rerun.exe"
            if not rerun_executable.is_file():
                raise FileNotFoundError(
                    "The Rerun executable was not found in the active environment."
                )
            self.viewer_process = subprocess.Popen(
                [
                    str(rerun_executable),
                    str(self.recording_path),
                    "--renderer=gl",
                    "--new",
                ]
            )
        except Exception as error:
            self._restore_after_run()
            messagebox.showerror("Simulation failed", str(error))
            return

        self.root.withdraw()
        self.root.after(250, self._wait_for_viewer)

    def _wait_for_viewer(self):
        if self.viewer_process.poll() is None:
            self.root.after(250, self._wait_for_viewer)
            return

        self._restore_after_run()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _restore_after_run(self):
        if self.recording_path is not None:
            self.recording_path.unlink(missing_ok=True)
        self.recording_path = None
        self.viewer_process = None
        self.run_button.configure(state="normal")
        self.status.configure(text="Ready for another run")


def show_parameter_window():
    root = tk.Tk()
    ParameterWindow(root)
    root.mainloop()
