
import sys
from pathlib import Path


def add_apogee_build_to_path():
    """Add the folder containing the compiled apogee module to sys.path."""
    project_root = Path(__file__).resolve().parents[2]
    build_root = project_root / "build"

    modules = [
        module
        for module_dir in (build_root / "Debug", build_root / "Release", build_root)
        for module in module_dir.glob("apogee*.pyd")
    ]

    if modules:
        newest_module = max(modules, key=lambda module: module.stat().st_mtime)
        sys.path.insert(0, str(newest_module.parent))
        return

    raise ModuleNotFoundError(
        "The compiled apogee module was not found."
    )
