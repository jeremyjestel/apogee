import os

from add_build_to_path import add_apogee_build_to_path


def main():
    os.environ.setdefault("WGPU_BACKEND", "gl")
    # Bootstrap at launch so importing the entry point does not load the UI.
    add_apogee_build_to_path()
    from parameter_window import show_parameter_window

    return show_parameter_window()


if __name__ == "__main__":
    raise SystemExit(main())
