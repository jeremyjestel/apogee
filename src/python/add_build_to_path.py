import os
import sys
import sysconfig
from pathlib import Path


_DLL_DIRECTORIES = []


def _build_configuration():
    requested = os.environ.get("APOGEE_BUILD_CONFIG", "Release").strip().lower()
    configs = {"debug": "Debug", "release": "Release"}
    try:
        return configs[requested]
    except KeyError:
        raise ValueError("APOGEE_BUILD_CONFIG must be Debug or Release") from None


def _module_directory(project_root, config, extension_suffix):
    build_root = project_root / "build"
    module_name = f"apogee{extension_suffix}"
    configured_directory = build_root / config
    if (configured_directory / module_name).is_file():
        return configured_directory

    # Ninja and Makefile generators put the module directly in the build directory.
    cache = build_root / "CMakeCache.txt"
    if (build_root / module_name).is_file() and cache.is_file():
        build_type = f"CMAKE_BUILD_TYPE:STRING={config}".casefold()
        cache_lines = cache.read_text(encoding="utf-8", errors="replace").splitlines()
        if build_type in (line.strip().casefold() for line in cache_lines):
            return build_root

    rebuild = f"Rebuild it with: cmake --build build --config {config}"
    raise ModuleNotFoundError(
        f"No compatible Apogee binding was found at '{configured_directory / module_name}'. "
        f"{rebuild}"
    )


def add_apogee_build_to_path():
    """Add a current, interpreter-compatible Apogee build to ``sys.path``."""
    project_root = Path(__file__).resolve().parents[2]
    config = _build_configuration()

    # Direct interpreter launches do not inherit Conda's activated DLL search path.
    if os.name == "nt" and not _DLL_DIRECTORIES:
        library_bin = Path(sys.prefix) / "Library" / "bin"
        if library_bin.is_dir():
            _DLL_DIRECTORIES.append(os.add_dll_directory(str(library_bin)))
            os.environ["PATH"] = f"{library_bin}{os.pathsep}{os.environ.get('PATH', '')}"

    # Use Python's own extension suffix so the selected binding matches this interpreter.
    extension_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not extension_suffix:
        raise RuntimeError("Python did not report an extension-module suffix.")

    module_dir = _module_directory(project_root, config, extension_suffix)
    module = module_dir / f"apogee{extension_suffix}"
    rebuild = f"Rebuild it with: cmake --build build --config {config}"

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
    sys.path[:] = [path for path in sys.path if path != module_dir_string]
    sys.path.insert(0, module_dir_string)
