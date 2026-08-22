import os
import sys
import sysconfig
from pathlib import Path


def add_apogee_build_to_path():
    """Add a current, interpreter-compatible Apogee build to ``sys.path``."""
    project_root = Path(__file__).resolve().parents[2]
    requested_config = os.environ.get("APOGEE_BUILD_CONFIG", "Release")
    configs = {"debug": "Debug", "release": "Release"}
    config = configs.get(requested_config.strip().lower())
    if config is None:
        raise ValueError("APOGEE_BUILD_CONFIG must be Debug or Release")

    module_dir = project_root / "build" / config
    extension_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not extension_suffix:
        raise RuntimeError("Python did not report an extension-module suffix.")

    module = module_dir / f"apogee{extension_suffix}"
    rebuild = f"Rebuild it with: cmake --build build --config {config}"
    if not module.is_file():
        raise ModuleNotFoundError(
            f"No compatible Apogee binding was found at '{module}'. {rebuild}"
        )

    cpp_root = project_root / "src" / "cpp"
    build_inputs = [project_root / "CMakeLists.txt"]
    build_inputs.extend(cpp_root.rglob("*.cpp"))
    build_inputs.extend(cpp_root.rglob("*.hpp"))
    newest_input = max(build_inputs, key=lambda path: path.stat().st_mtime_ns)
    if module.stat().st_mtime_ns < newest_input.stat().st_mtime_ns:
        relative_input = newest_input.relative_to(project_root)
        raise ImportError(
            f"The {config} Apogee binding is older than '{relative_input}'. "
            f"{rebuild}"
        )

    module_dir_string = str(module_dir)
    if module_dir_string not in sys.path:
        sys.path.insert(0, module_dir_string)
