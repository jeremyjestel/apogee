import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import apogee

from visualization import save_result
from visualization.viewer_session import ViewerSession


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
        self.viewer_session = ViewerSession()
        self.run_thread = None
        self.run_messages = queue.SimpleQueue()
        self.cancel_run = threading.Event()

        root.title("Apogee Simulation Parameters")
        root.geometry("720x820")
        root.minsize(560, 500)
        root.after_idle(lambda: root.state("zoomed"))
        root.protocol("WM_DELETE_WINDOW", self._close)

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
        def scroll_form(event):
            canvas.yview_scroll(-event.delta // 120, "units")

        canvas.bind(
            "<Enter>",
            lambda event: self.root.bind_all("<MouseWheel>", scroll_form),
        )
        canvas.bind(
            "<Leave>",
            lambda event: self.root.unbind_all("<MouseWheel>"),
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
        values = {path: entry.get() for path, entry in self.entries.items()}
        window_size = (
            self.root.winfo_screenwidth(),
            self.root.winfo_screenheight(),
        )
        self.cancel_run.clear()
        self.run_thread = threading.Thread(
            target=self._run_worker,
            args=(values, window_size),
            name="apogee-simulation",
            daemon=True,
        )
        self.run_thread.start()
        self.root.after(100, self._wait_for_simulation)

    def _run_worker(self, values, window_size):
        try:
            params = create_params_from_text(values)
            result = apogee.run_sim(params)
            if self.cancel_run.is_set():
                return
            self.viewer_session.start(
                lambda recording_path: save_result(result, recording_path),
                window_size=window_size,
            )
        except Exception as error:
            self.run_messages.put(error)
            return
        self.run_messages.put(None)

    def _wait_for_simulation(self):
        if self.run_thread.is_alive():
            self.root.after(100, self._wait_for_simulation)
            return

        error = self.run_messages.get()
        self.run_thread = None
        if error is not None:
            self._restore_after_run()
            messagebox.showerror("Simulation failed", str(error))
            return

        # Hide this window while Rerun is open, then poll without blocking Tk.
        self.root.withdraw()
        self.root.after(250, self._wait_for_viewer)

    def _wait_for_viewer(self):
        # Reschedule the check until the external viewer process has exited.
        if self.viewer_session.poll() is None:
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
        self.viewer_session.cleanup()
        self.run_button.configure(state="normal")
        self.status.configure(text="Ready for another run")

    def _close(self):
        self.cancel_run.set()
        self.viewer_session.cleanup()
        self.root.destroy()


def show_parameter_window():
    root = tk.Tk()
    ParameterWindow(root)
    root.mainloop()
