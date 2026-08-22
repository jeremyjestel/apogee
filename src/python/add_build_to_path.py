
import os
import sys
import sysconfig
from pathlib import Path


BUILD_CONFIGS = {
    "debug": "Debug",
    "release": "Release",
    "relwithdebinfo": "RelWithDebInfo",
    "minsizerel": "MinSizeRel",
}
CPP_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".inc"}


def _selected_build_config():
    requested = os.environ.get("APOGEE_BUILD_CONFIG", "Release").strip()
    config = BUILD_CONFIGS.get(requested.lower())
    if config is None:
        supported = ", ".join(BUILD_CONFIGS.values())
        raise ValueError(
            f"Unsupported APOGEE_BUILD_CONFIG '{requested}'. "
            f"Choose one of: {supported}."
        )
    return config


def _rebuild_message(config):
    return f"Rebuild it with: cmake --build build --config {config}"


def _newest_build_input(project_root):
    inputs = [project_root / "CMakeLists.txt"]
    cpp_root = project_root / "src" / "cpp"
    inputs.extend(
        path
        for path in cpp_root.rglob("*")
        if path.is_file() and path.suffix.lower() in CPP_SOURCE_SUFFIXES
    )
    return max(inputs, key=lambda path: path.stat().st_mtime_ns)


def add_apogee_build_to_path():
    """Add a current, interpreter-compatible Apogee build to ``sys.path``."""
    project_root = Path(__file__).resolve().parents[2]
    config = _selected_build_config()
    module_dir = project_root / "build" / config
    extension_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    if not extension_suffix:
        raise RuntimeError("Python did not report an extension-module suffix.")

    module = module_dir / f"apogee{extension_suffix}"
    if not module.is_file():
        raise ModuleNotFoundError(
            f"No Apogee binding compatible with this Python interpreter was "
            f"found at '{module}'. {_rebuild_message(config)}"
        )

    newest_input = _newest_build_input(project_root)
    if module.stat().st_mtime_ns < newest_input.stat().st_mtime_ns:
        relative_input = newest_input.relative_to(project_root)
        raise ImportError(
            f"The {config} Apogee binding is older than '{relative_input}'. "
            f"{_rebuild_message(config)}"
        )

    module_dir_string = str(module_dir)
    if module_dir_string not in sys.path:
        sys.path.insert(0, module_dir_string)
