
import sys
from pathlib import Path


def add_apogee_build_to_path():
    """Add the folder containing the compiled apogee module to sys.path."""
    project_root = Path(__file__).resolve().parents[2]
    build_root = project_root / "build"

    for module_dir in (build_root / "Debug", build_root / "Release", build_root):
        if next(module_dir.glob("apogee*.pyd"), None) is not None:
            sys.path.insert(0, str(module_dir))
            return

    raise ModuleNotFoundError(
        "The compiled apogee module was not found."
    )
