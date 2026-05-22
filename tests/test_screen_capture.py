"""Tests for screen_capture.

The Gdk + ImageMagick + portal backends each require a display
server / external program / D-Bus; we mock them all and verify
the chain logic, callback contracts, and error paths.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestRegionValidation:
    def test_zero_width_fires_error_callback(self):
        from orca_ext_utils.screen_capture import capture_region_async

        captured: list[tuple] = []
        capture_region_async(0, 0, 0, 100, lambda png, err: captured.append((png, err)))
        assert len(captured) == 1
        png, err = captured[0]
        assert png is None
        assert err is not None
        assert "invalid" in err.lower()

    def test_negative_height_fires_error_callback(self):
        from orca_ext_utils.screen_capture import capture_region_async

        captured: list[tuple] = []
        capture_region_async(0, 0, 100, -1, lambda png, err: captured.append((png, err)))
        assert len(captured) == 1
        assert captured[0][0] is None
        assert "invalid" in captured[0][1].lower()


class TestBackendChain:
    def test_gdk_success_short_circuits(self, monkeypatch):
        from orca_ext_utils import screen_capture

        monkeypatch.setattr(
            screen_capture, "_capture_via_gdk",
            lambda x, y, w, h: b"fake_png_bytes",
        )
        # imagemagick + portal should not be called.
        monkeypatch.setattr(
            screen_capture, "_capture_via_imagemagick",
            mock.Mock(side_effect=RuntimeError("should not run")),
        )
        monkeypatch.setattr(
            screen_capture, "_capture_via_portal_async",
            mock.Mock(side_effect=RuntimeError("should not run")),
        )

        captured: list[tuple] = []
        screen_capture.capture_region_async(
            0, 0, 100, 100,
            lambda png, err: captured.append((png, err)),
        )
        assert captured == [(b"fake_png_bytes", None)]

    def test_gdk_fail_falls_to_imagemagick(self, monkeypatch):
        from orca_ext_utils import screen_capture

        monkeypatch.setattr(
            screen_capture, "_capture_via_gdk", lambda x, y, w, h: None,
        )
        monkeypatch.setattr(
            screen_capture, "_capture_via_imagemagick",
            lambda x, y, w, h: b"imagemagick_bytes",
        )
        portal_mock = mock.Mock()
        monkeypatch.setattr(
            screen_capture, "_capture_via_portal_async", portal_mock,
        )

        captured: list[tuple] = []
        screen_capture.capture_region_async(
            0, 0, 100, 100,
            lambda png, err: captured.append((png, err)),
        )
        assert captured == [(b"imagemagick_bytes", None)]
        portal_mock.assert_not_called()

    def test_both_x11_fail_falls_to_portal(self, monkeypatch):
        from orca_ext_utils import screen_capture

        monkeypatch.setattr(
            screen_capture, "_capture_via_gdk", lambda x, y, w, h: None,
        )
        monkeypatch.setattr(
            screen_capture, "_capture_via_imagemagick", lambda x, y, w, h: None,
        )
        portal_mock = mock.Mock()
        monkeypatch.setattr(
            screen_capture, "_capture_via_portal_async", portal_mock,
        )

        called_back: list[tuple] = []
        screen_capture.capture_region_async(
            0, 0, 100, 100,
            lambda png, err: called_back.append((png, err)),
        )
        # Portal called; our user callback NOT called synchronously
        # (portal is async).
        assert portal_mock.call_count == 1
        assert called_back == []

    def test_gdk_exception_continues_chain(self, monkeypatch):
        from orca_ext_utils import screen_capture

        def gdk_boom(x, y, w, h):
            raise RuntimeError("gdk crashed")
        monkeypatch.setattr(screen_capture, "_capture_via_gdk", gdk_boom)
        monkeypatch.setattr(
            screen_capture, "_capture_via_imagemagick",
            lambda x, y, w, h: b"fallback",
        )

        captured: list[tuple] = []
        screen_capture.capture_region_async(
            0, 0, 100, 100,
            lambda png, err: captured.append((png, err)),
        )
        # gdk crash should not abort; imagemagick provides bytes.
        assert captured == [(b"fallback", None)]


class TestUpscale:
    def test_factor_one_returns_input_unchanged(self):
        from orca_ext_utils.screen_capture import upscale_png

        # factor <= 1.0 is a no-op short-circuit.
        assert upscale_png(b"original", 1.0) == b"original"
        assert upscale_png(b"original", 0.5) == b"original"

    def test_returns_input_on_invalid_png(self):
        from orca_ext_utils.screen_capture import upscale_png

        # Garbage input: should fall through to the return-input path.
        result = upscale_png(b"not_a_png", 2.0)
        assert result == b"not_a_png"
