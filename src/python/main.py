from add_build_to_path import add_apogee_build_to_path
import os
os.environ["WGPU_BACKEND"] = "gl"

# Make the compiled binding importable before loading modules that depend on it.
add_apogee_build_to_path()

from parameter_window import show_parameter_window


def main():
    return show_parameter_window()


if __name__ == "__main__":
    raise SystemExit(main())
