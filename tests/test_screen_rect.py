"""Tests for screen_rect.

Mock-heavy: the production code talks to Atspi and Gdk, both of
which need a live display to actually function. These tests pin
the dispatch logic (which backend gets tried, in what order, what
constitutes "invalid extents" and triggers fallback) without
requiring a display.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def clear_backend_cache():
    from orca_ext_utils import _backend
    _backend.is_x11.cache_clear()
    _backend.is_wayland.cache_clear()
    yield
    _backend.is_x11.cache_clear()
    _backend.is_wayland.cache_clear()


class TestForAccessible:
    def test_none_input_returns_none(self):
        from orca_ext_utils import screen_rect
        assert screen_rect.for_accessible(None) is None

    def test_atspi_success_returns_rect(self):
        from orca_ext_utils import screen_rect
        rect = SimpleNamespace(x=100, y=200, width=300, height=400)
        obj = mock.Mock()
        obj.get_extents = mock.Mock(return_value=rect)
        with mock.patch.object(
            screen_rect, "_try_atspi_screen_extents",
            return_value=(100, 200, 300, 400),
        ):
            result = screen_rect.for_accessible(obj)
        assert result == (100, 200, 300, 400)

    def test_atspi_invalid_falls_back_to_window_relative(self, monkeypatch):
        from orca_ext_utils import screen_rect
        monkeypatch.setattr(screen_rect._backend, "is_x11", lambda: True)
        monkeypatch.setattr(screen_rect, "_try_atspi_screen_extents", lambda _: None)
        monkeypatch.setattr(
            screen_rect, "_try_window_relative_fallback",
            lambda _: (50, 60, 70, 80),
        )
        result = screen_rect.for_accessible(mock.Mock())
        assert result == (50, 60, 70, 80)

    def test_wayland_no_fallback(self, monkeypatch):
        from orca_ext_utils import screen_rect
        monkeypatch.setattr(screen_rect._backend, "is_x11", lambda: False)
        monkeypatch.setattr(screen_rect, "_try_atspi_screen_extents", lambda _: None)
        # Even if fallback were called it would return junk; the
        # test asserts fallback is NOT called.
        sentinel = mock.Mock(return_value=(0, 0, 0, 0))
        monkeypatch.setattr(screen_rect, "_try_window_relative_fallback", sentinel)
        result = screen_rect.for_accessible(mock.Mock())
        assert result is None
        sentinel.assert_not_called()

    def test_obj_with_no_get_extents_returns_none(self, monkeypatch):
        from orca_ext_utils import screen_rect
        # Simulate the atspi import failing or the object lacking
        # get_extents -- _try_atspi_screen_extents swallows and returns None.
        # On X11, fallback should still try (and may also return None).
        monkeypatch.setattr(screen_rect._backend, "is_x11", lambda: True)
        monkeypatch.setattr(screen_rect, "_try_window_relative_fallback", lambda _: None)
        obj = SimpleNamespace()  # no get_extents
        result = screen_rect.for_accessible(obj)
        assert result is None


class TestAtspiInvalidSentinels:
    """The Atspi extents path treats certain values as 'unknown'."""

    @pytest.mark.parametrize(
        "rect,expected_none",
        [
            (SimpleNamespace(x=-1, y=-1, width=100, height=100), True),
            (SimpleNamespace(x=0, y=0, width=0, height=100), True),
            (SimpleNamespace(x=0, y=0, width=100, height=0), True),
            (SimpleNamespace(x=0, y=0, width=-5, height=100), True),
            (SimpleNamespace(x=0, y=0, width=100, height=100), False),
            (SimpleNamespace(x=10, y=20, width=300, height=400), False),
        ],
    )
    def test_invalid_extents_returns_none(self, rect, expected_none):
        from orca_ext_utils import screen_rect
        obj = mock.Mock()
        obj.get_extents = mock.Mock(return_value=rect)
        result = screen_rect._try_atspi_screen_extents(obj)
        if expected_none:
            assert result is None
        else:
            assert result is not None
            assert result[2] == rect.width
            assert result[3] == rect.height

    def test_get_extents_raises_returns_none(self):
        from orca_ext_utils import screen_rect
        obj = mock.Mock()
        obj.get_extents = mock.Mock(side_effect=RuntimeError("kaboom"))
        assert screen_rect._try_atspi_screen_extents(obj) is None
