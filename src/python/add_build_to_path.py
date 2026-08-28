import os
import sys
import sysconfig
from pathlib import Path


_DLL_DIRECTORIES = []


def add_apogee_build_to_path():
    """Add a current, interpreter-compatible Apogee build to ``sys.path``."""
    project_root = Path(__file__).resolve().parents[2]

    # Direct interpreter launches do not inherit Conda's activated DLL search path.
    if os.name == "nt" and not _DLL_DIRECTORIES:
        library_bin = Path(sys.prefix) / "Library" / "bin"
        if library_bin.is_dir():
            _DLL_DIRECTORIES.append(os.add_dll_directory(str(library_bin)))
            os.environ["PATH"] = f"{library_bin}{os.pathsep}{os.environ.get('PATH', '')}"

    # Normalize the requested CMake configuration to its on-disk directory name.
    requested_config = os.environ.get("APOGEE_BUILD_CONFIG", "Release")
    configs = {"debug": "Debug", "release": "Release"}
    config = configs.get(requested_config.strip().lower())
    if config is None:
        raise ValueError("APOGEE_BUILD_CONFIG must be Debug or Release")

    # Use Python's own extension suffix so the selected binding matches this interpreter.
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

    # Require a rebuild whenever any C++ source or build definition is newer than the module.
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

    # Put the selected build first so another Apogee installation cannot shadow it.
    module_dir_string = str(module_dir)
    if module_dir_string not in sys.path:
        sys.path.insert(0, module_dir_string)
