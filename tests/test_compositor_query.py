"""Tests for compositor_query.

The Gdk display calls are mocked because pytest runs without a
default display in CI / headless. The pure-Python virtual screen
rect calculation is verified directly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestVirtualScreenRect:
    def test_single_monitor(self, monkeypatch):
        from orca_ext_utils import compositor_query
        from orca_ext_utils.compositor_query import MonitorInfo

        fake_monitor = MonitorInfo(
            index=0, rect=(0, 0, 1920, 1080),
            scale_factor=1, refresh_hz=60.0, model="Acme",
            is_primary=True,
        )
        monkeypatch.setattr(compositor_query, "monitors", lambda: (fake_monitor,))
        assert compositor_query.virtual_screen_rect() == (0, 0, 1920, 1080)

    def test_dual_monitor_horizontal(self, monkeypatch):
        from orca_ext_utils import compositor_query
        from orca_ext_utils.compositor_query import MonitorInfo

        left = MonitorInfo(
            index=0, rect=(0, 0, 1920, 1080),
            scale_factor=1, refresh_hz=60.0, model="Acme",
            is_primary=True,
        )
        right = MonitorInfo(
            index=1, rect=(1920, 0, 2560, 1440),
            scale_factor=1, refresh_hz=144.0, model="Acme Pro",
            is_primary=False,
        )
        monkeypatch.setattr(compositor_query, "monitors", lambda: (left, right))
        rect = compositor_query.virtual_screen_rect()
        # Union: starts at (0,0), extends to (1920+2560, max(1080,1440)).
        assert rect == (0, 0, 4480, 1440)

    def test_monitors_with_negative_origin(self, monkeypatch):
        from orca_ext_utils import compositor_query
        from orca_ext_utils.compositor_query import MonitorInfo

        # Common case: secondary monitor placed to the left of primary,
        # so its x is negative.
        left = MonitorInfo(
            index=1, rect=(-1920, 0, 1920, 1080),
            scale_factor=1, refresh_hz=60.0, model="left",
            is_primary=False,
        )
        right = MonitorInfo(
            index=0, rect=(0, 0, 1920, 1080),
            scale_factor=1, refresh_hz=60.0, model="right",
            is_primary=True,
        )
        monkeypatch.setattr(compositor_query, "monitors", lambda: (left, right))
        # Virtual screen origin should be -1920, 0; width 3840.
        assert compositor_query.virtual_screen_rect() == (-1920, 0, 3840, 1080)

    def test_empty_monitor_list_returns_none(self, monkeypatch):
        from orca_ext_utils import compositor_query

        monkeypatch.setattr(compositor_query, "monitors", lambda: ())
        assert compositor_query.virtual_screen_rect() is None


class TestMonitorInfo:
    def test_named_tuple_fields(self):
        from orca_ext_utils.compositor_query import MonitorInfo

        info = MonitorInfo(
            index=0, rect=(0, 0, 1920, 1080),
            scale_factor=2, refresh_hz=120.0, model="Test",
            is_primary=True,
        )
        # Verify named-tuple access works as documented.
        assert info.index == 0
        assert info.rect == (0, 0, 1920, 1080)
        assert info.scale_factor == 2
        assert info.refresh_hz == 120.0
        assert info.model == "Test"
        assert info.is_primary is True


class TestNoDisplay:
    def test_monitors_returns_empty_with_no_display(self, monkeypatch):
        from orca_ext_utils import compositor_query

        monkeypatch.setattr(compositor_query, "_get_display", lambda: None)
        assert compositor_query.monitors() == ()

    def test_primary_monitor_none_with_no_display(self, monkeypatch):
        from orca_ext_utils import compositor_query

        monkeypatch.setattr(compositor_query, "_get_display", lambda: None)
        assert compositor_query.primary_monitor() is None

    def test_monitor_at_point_none_with_no_display(self, monkeypatch):
        from orca_ext_utils import compositor_query

        monkeypatch.setattr(compositor_query, "_get_display", lambda: None)
        assert compositor_query.monitor_at_point(100, 100) is None
