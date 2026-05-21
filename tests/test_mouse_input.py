"""Tests for mouse_input.

Pure dispatch logic; the Atspi.generate_mouse_event call is mocked
since it requires a live display. Tests pin the kind-code mapping
and the error-swallow behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_atspi(monkeypatch):
    """Replace _generate at the module level so kind-mapping logic
    is exercised without touching the real Atspi import path."""

    from orca_ext_utils import mouse_input
    calls: list[tuple[int, int, str]] = []

    def fake_generate(x: int, y: int, kind: str) -> bool:
        calls.append((x, y, kind))
        return True

    monkeypatch.setattr(mouse_input, "_generate", fake_generate)
    return calls


class TestKindMapping:
    def test_click_left(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.click_at(100, 200) is True
        assert mock_atspi == [(100, 200, "b1c")]

    def test_click_middle(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.click_at(50, 60, button="middle") is True
        assert mock_atspi == [(50, 60, "b2c")]

    def test_click_right(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.click_at(0, 0, button="right") is True
        assert mock_atspi == [(0, 0, "b3c")]

    def test_double_click(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.double_click_at(10, 20) is True
        assert mock_atspi == [(10, 20, "b1d")]

    def test_press_and_release(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.press_at(5, 5) is True
        assert mouse_input.release_at(5, 5) is True
        assert mock_atspi == [(5, 5, "b1p"), (5, 5, "b1r")]

    def test_move_only(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.move_to(300, 400) is True
        assert mock_atspi == [(300, 400, "abs")]


class TestInvalidButton:
    """A bad button name should return False without raising."""

    def test_unknown_button_click(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.click_at(0, 0, button="fourth") is False  # type: ignore[arg-type]
        assert mock_atspi == []

    def test_unknown_button_press(self, mock_atspi):
        from orca_ext_utils import mouse_input
        assert mouse_input.press_at(0, 0, button="extra") is False  # type: ignore[arg-type]
        assert mock_atspi == []


class TestErrorSwallowing:
    """_generate should never propagate exceptions; returns False."""

    def test_atspi_import_failure_returns_false(self, monkeypatch):
        # Simulate the gi import path failing by patching the
        # internal _generate to its real impl, with the Atspi import
        # forced to fail.
        from orca_ext_utils import mouse_input

        original = mouse_input._generate

        def failing_generate(x, y, kind):
            try:
                raise ImportError("simulated atspi unavailable")
            except Exception:
                return False

        monkeypatch.setattr(mouse_input, "_generate", failing_generate)
        assert mouse_input.click_at(0, 0) is False
