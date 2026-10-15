import importlib
import os
import sys
from types import SimpleNamespace

import pytest

import add_build_to_path as bootstrap
import main


@pytest.fixture
def fake_build(tmp_path, monkeypatch):
    source = tmp_path / "src" / "python" / "add_build_to_path.py"
    source.parent.mkdir(parents=True)
    source.touch()
    (tmp_path / "src" / "cpp").mkdir()
    definition = tmp_path / "CMakeLists.txt"
    definition.touch()
    module_dir = tmp_path / "build" / "Release"
    module_dir.mkdir(parents=True)
    suffix = bootstrap.sysconfig.get_config_var("EXT_SUFFIX")
    module = module_dir / f"apogee{suffix}"
    module.touch()
    # Use explicit timestamps, independent of filesystem clock precision.
    os.utime(definition, (100, 100))
    os.utime(module, (200, 200))
    monkeypatch.setattr(bootstrap, "__file__", str(source))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("APOGEE_BUILD_CONFIG", "Release")
    return tmp_path, module


def test_bootstrap_prioritizes_selected_binding_without_duplicate_paths(fake_build):
    unused_root, module = fake_build
    sys.path.append(str(module.parent))

    bootstrap.add_apogee_build_to_path()
    bootstrap.add_apogee_build_to_path()

    assert sys.path[0] == str(module.parent)
    assert sys.path.count(str(module.parent)) == 1


def test_bootstrap_rejects_stale_binding(fake_build):
    root, unused_module = fake_build
    header = root / "src" / "cpp" / "new_system.hpp"
    header.touch()
    os.utime(header, (300, 300))

    with pytest.raises(ImportError, match="new_system.hpp"):
        bootstrap.add_apogee_build_to_path()


def test_bootstrap_requires_an_interpreter_compatible_binding(fake_build):
    unused_root, module = fake_build
    module.rename(module.with_name("apogee.wrong-python.pyd"))

    with pytest.raises(ModuleNotFoundError, match="No compatible Apogee binding"):
        bootstrap.add_apogee_build_to_path()


@pytest.mark.parametrize("config", ["Debug", "Release"])
def test_bootstrap_supports_single_configuration_builds(fake_build, monkeypatch, config):
    root, module = fake_build
    module = module.rename(root / "build" / module.name)
    (root / "build" / "CMakeCache.txt").write_text(
        f"CMAKE_BUILD_TYPE:STRING={config}\n", encoding="utf-8"
    )
    monkeypatch.setenv("APOGEE_BUILD_CONFIG", config)

    bootstrap.add_apogee_build_to_path()

    assert sys.path[0] == str(module.parent)


def test_bootstrap_does_not_load_a_different_single_build_configuration(fake_build):
    root, module = fake_build
    module.rename(root / "build" / module.name)
    (root / "build" / "CMakeCache.txt").write_text(
        "CMAKE_BUILD_TYPE:STRING=Debug\n", encoding="utf-8"
    )

    with pytest.raises(ModuleNotFoundError):
        bootstrap.add_apogee_build_to_path()


def test_importing_entry_point_does_not_bootstrap_or_change_environment(monkeypatch):
    original_bootstrap = bootstrap.add_apogee_build_to_path

    def unexpected_bootstrap():
        pytest.fail("Importing the entry point initialized the application")

    monkeypatch.setattr(bootstrap, "add_apogee_build_to_path", unexpected_bootstrap)
    monkeypatch.delenv("WGPU_BACKEND", raising=False)
    try:
        importlib.reload(main)
        assert "WGPU_BACKEND" not in os.environ
    finally:
        # reload() replaces module attributes outside monkeypatch's tracking.
        main.add_apogee_build_to_path = original_bootstrap


@pytest.mark.parametrize("backend", [None, "vulkan"])
def test_launch_bootstraps_before_opening_ui_and_respects_backend(monkeypatch, backend):
    calls = []
    if backend is None:
        monkeypatch.delenv("WGPU_BACKEND", raising=False)
    else:
        monkeypatch.setenv("WGPU_BACKEND", backend)
    monkeypatch.setattr(main, "add_apogee_build_to_path", lambda: calls.append("bootstrap"))

    def show_window():
        calls.append("window")
        return 7

    monkeypatch.setitem(sys.modules, "parameter_window", SimpleNamespace(show_parameter_window=show_window))

    assert main.main() == 7
    assert calls == ["bootstrap", "window"]
    assert os.environ["WGPU_BACKEND"] == (backend or "gl")
