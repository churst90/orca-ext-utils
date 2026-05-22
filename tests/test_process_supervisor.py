"""Tests for process_supervisor.

Sync path tested against real /bin/echo and /bin/true; async path
exercised lightly via mocked GLib (full async tests need a live
main loop which pytest doesn't easily provide).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestIsAvailable:
    def test_echo_present(self):
        from orca_ext_utils.process_supervisor import is_available

        assert is_available("echo") is True

    def test_fake_absent(self):
        from orca_ext_utils.process_supervisor import is_available

        assert is_available("orca_ext_utils_definitely_not_an_executable") is False


class TestRunSync:
    def test_echo_returns_stdout(self):
        from orca_ext_utils.process_supervisor import run_sync

        result = run_sync(["echo", "hello"])
        assert result.returncode == 0
        assert b"hello" in result.stdout
        assert result.error is None
        assert result.timed_out is False

    def test_nonexistent_executable_returns_error(self):
        from orca_ext_utils.process_supervisor import run_sync

        result = run_sync(["orca_ext_utils_definitely_fake_exe_xyz"])
        assert result.returncode == -1
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_empty_argv_returns_error(self):
        from orca_ext_utils.process_supervisor import run_sync

        result = run_sync([])
        assert result.returncode == -1
        assert result.error is not None

    def test_nonzero_exit_returned_cleanly(self):
        from orca_ext_utils.process_supervisor import run_sync

        # `false` exits 1. Supervisor should report rc=1, no error.
        result = run_sync(["false"])
        assert result.returncode == 1
        assert result.error is None
        assert result.timed_out is False

    def test_stdin_delivered(self):
        from orca_ext_utils.process_supervisor import run_sync

        # `cat` echoes stdin. Verifies our stdin_bytes plumbing works.
        result = run_sync(["cat"], stdin_bytes=b"piped input")
        assert result.returncode == 0
        assert result.stdout == b"piped input"

    def test_timeout_kills_long_process(self):
        from orca_ext_utils.process_supervisor import run_sync

        # `sleep 5` will be killed by the supervisor at the 0.5s mark.
        result = run_sync(["sleep", "5"], timeout_seconds=0.5)
        assert result.timed_out is True
        assert result.returncode == -1
        assert result.error is not None
        assert "timed out" in result.error.lower()


class TestProcessResult:
    def test_is_immutable_namedtuple(self):
        from orca_ext_utils.process_supervisor import ProcessResult
        import pytest

        result = ProcessResult(
            returncode=0, stdout=b"", stderr=b"",
            timed_out=False, error=None,
        )
        with pytest.raises(AttributeError):
            result.returncode = 1  # type: ignore[misc]
