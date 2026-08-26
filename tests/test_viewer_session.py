import os

import pytest

from visualization import viewer_session


def test_find_rerun_prefers_the_active_environment(monkeypatch, tmp_path):
    environment = tmp_path / "environment"
    if os.name == "nt":
        executable = environment / "Scripts" / "rerun.exe"
        python = environment / "python.exe"
    else:
        executable = environment / "bin" / "rerun"
        python = environment / "bin" / "python"
    executable.parent.mkdir(parents=True)
    executable.touch()
    python.touch()

    monkeypatch.setattr(viewer_session.sys, "prefix", str(environment))
    monkeypatch.setattr(viewer_session.sys, "executable", str(python))
    monkeypatch.setattr(
        viewer_session.shutil,
        "which",
        lambda unused_name: str(tmp_path / "path-rerun"),
    )

    assert viewer_session.find_rerun_executable() == executable


def test_viewer_session_owns_recording_and_process_lifecycle(monkeypatch, tmp_path):
    executable = tmp_path / "rerun.exe"
    executable.touch()

    class Process:
        def __init__(self, arguments, **options):
            self.arguments = arguments
            self.options = options
            self.pid = 123
            self.exit_code = None

        def poll(self):
            return self.exit_code

    launched = []

    def launch(arguments, **options):
        process = Process(arguments, **options)
        launched.append(process)
        return process

    monkeypatch.setattr(
        viewer_session,
        "find_rerun_executable",
        lambda unused_request=None: executable,
    )
    monkeypatch.setattr(viewer_session.subprocess, "Popen", launch)
    monkeypatch.setattr(
        viewer_session,
        "_maximize_process_window",
        lambda unused_pid: True,
    )

    session = viewer_session.ViewerSession()
    recording = session.start(
        lambda path: path.write_bytes(b"recording"),
        window_size=(1920, 1080),
    )

    assert recording.is_file()
    assert launched[0].arguments == [
        str(executable),
        str(recording),
        "--renderer=gl",
        "--window-size=1920x1080",
        "--new",
    ]
    assert session.poll() is None

    launched[0].exit_code = 0
    assert session.poll() == 0
    session.cleanup()
    assert session.recording_path is None
    assert not recording.exists()


def test_explicit_missing_viewer_path_is_actionable(tmp_path):
    missing = tmp_path / "missing-rerun"
    with pytest.raises(FileNotFoundError) as error:
        viewer_session.find_rerun_executable(missing)
    assert str(missing) in str(error.value)
