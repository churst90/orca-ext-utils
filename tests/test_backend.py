"""Tests for backend detection (X11 vs Wayland)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Reset the cached results between tests; the production code
    uses functools.lru_cache so a single process never re-checks."""

    from orca_ext_utils import _backend
    _backend.is_x11.cache_clear()
    _backend.is_wayland.cache_clear()
    yield
    _backend.is_x11.cache_clear()
    _backend.is_wayland.cache_clear()


class TestEnvFallback:
    """When Gdk isn't available, we should fall back to env vars."""

    def test_wayland_env_yields_wayland(self, monkeypatch):
        from orca_ext_utils import _backend
        monkeypatch.setattr(_backend, "_gdk_says_x11", lambda: False)
        monkeypatch.setattr(_backend, "_gdk_says_wayland", lambda: False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.delenv("DISPLAY", raising=False)
        assert _backend.is_wayland() is True
        assert _backend.is_x11() is False

    def test_display_env_yields_x11(self, monkeypatch):
        from orca_ext_utils import _backend
        monkeypatch.setattr(_backend, "_gdk_says_x11", lambda: False)
        monkeypatch.setattr(_backend, "_gdk_says_wayland", lambda: False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setenv("DISPLAY", ":0")
        assert _backend.is_x11() is True
        assert _backend.is_wayland() is False

    def test_no_env_yields_both_false(self, monkeypatch):
        from orca_ext_utils import _backend
        monkeypatch.setattr(_backend, "_gdk_says_x11", lambda: False)
        monkeypatch.setattr(_backend, "_gdk_says_wayland", lambda: False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        assert _backend.is_x11() is False
        assert _backend.is_wayland() is False


class TestGdkPrecedence:
    """Gdk display class is more authoritative than env vars."""

    def test_gdk_x11_wins_over_wayland_env(self, monkeypatch):
        from orca_ext_utils import _backend
        monkeypatch.setattr(_backend, "_gdk_says_x11", lambda: True)
        monkeypatch.setattr(_backend, "_gdk_says_wayland", lambda: False)
        # XDG_SESSION_TYPE=wayland is the classic Fedora MATE-on-X11
        # lie. Gdk's display class is what actually matters.
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        assert _backend.is_x11() is True
        assert _backend.is_wayland() is False

    def test_gdk_wayland_wins_over_display_env(self, monkeypatch):
        from orca_ext_utils import _backend
        monkeypatch.setattr(_backend, "_gdk_says_x11", lambda: False)
        monkeypatch.setattr(_backend, "_gdk_says_wayland", lambda: True)
        monkeypatch.setenv("DISPLAY", ":0")
        assert _backend.is_wayland() is True
        assert _backend.is_x11() is False
