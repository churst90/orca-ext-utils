"""Tests for keyboard_grab.

Pure logic: keysym filtering, modifier-combo enumeration, failure
tracking. AT-SPI device construction is mocked since it requires a
live AT-SPI bus.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestConstruction:
    def test_default_modifier_combos(self):
        from orca_ext_utils.keyboard_grab import KeysetGrab, DEFAULT_MODIFIER_COMBOS

        grab = KeysetGrab([0x61, 0x62])  # XK_a, XK_b
        assert list(grab._modifier_combos) == list(DEFAULT_MODIFIER_COMBOS)
        assert grab._keysyms == [0x61, 0x62]

    def test_explicit_modifier_combos(self):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        grab = KeysetGrab([0x61], modifier_combos=[0, 0x04])
        assert grab._modifier_combos == [0, 0x04]

    def test_invalid_keysyms_filtered(self):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        # Zero and negative keysyms are dropped (sentinel "no mapping").
        grab = KeysetGrab([0x61, 0, -1, 0x62])
        assert grab._keysyms == [0x61, 0x62]


class TestGrabRegistration:
    def test_enter_no_device_is_noop(self, monkeypatch):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        monkeypatch.setattr(KeysetGrab, "_get_device", staticmethod(lambda: None))
        with KeysetGrab([0x61]) as grab:
            assert grab._device is None
            assert grab.failed_keysyms == []
            assert grab._grab_ids == []

    def test_failed_grabs_are_tracked(self, monkeypatch):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        device = mock.Mock()
        # add_key_grab returns 0 for every call: simulate "another
        # process already holds this grab" or "Wayland compositor
        # refused."
        device.add_key_grab = mock.Mock(return_value=0)
        monkeypatch.setattr(KeysetGrab, "_get_device", staticmethod(lambda: device))
        # Stub the Atspi import that __enter__ does. Need a fake
        # gi.repository.Atspi with a KeyDefinition() factory.
        fake_atspi = mock.Mock()
        fake_atspi.KeyDefinition = mock.Mock(side_effect=lambda: mock.Mock())
        # We patch the import inside __enter__ -- monkeypatch sys.modules.
        monkeypatch.setitem(sys.modules, "gi", mock.Mock())
        sys.modules["gi"].require_version = mock.Mock()
        fake_repo = mock.Mock()
        fake_repo.Atspi = fake_atspi
        monkeypatch.setitem(sys.modules, "gi.repository", fake_repo)
        try:
            with KeysetGrab([0x61, 0x62], modifier_combos=[0]) as grab:
                # Both keysyms with the single modifier combo should
                # have failed.
                assert grab.failed_keysyms == [(0x61, 0), (0x62, 0)]
                assert grab._grab_ids == []
        finally:
            sys.modules.pop("gi", None)
            sys.modules.pop("gi.repository", None)


class TestRelease:
    def test_release_calls_remove_for_each_grab(self, monkeypatch):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        device = mock.Mock()
        # Two successful grabs.
        device.add_key_grab = mock.Mock(side_effect=[101, 102])
        device.remove_key_grab = mock.Mock()

        grab = KeysetGrab([0x61, 0x62], modifier_combos=[0])
        # Bypass __enter__ to directly install the grab list -- testing
        # the release path in isolation.
        grab._device = device
        grab._grab_ids = [(0x61, 0, 101), (0x62, 0, 102)]
        grab.release()
        assert device.remove_key_grab.call_count == 2
        assert grab._grab_ids == []

    def test_release_swallows_errors(self, monkeypatch):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        device = mock.Mock()
        device.remove_key_grab = mock.Mock(side_effect=RuntimeError("bad"))

        grab = KeysetGrab([0x61])
        grab._device = device
        grab._grab_ids = [(0x61, 0, 101)]
        # Should not raise.
        grab.release()
        assert grab._grab_ids == []


class TestContextManager:
    def test_exits_call_release(self, monkeypatch):
        from orca_ext_utils.keyboard_grab import KeysetGrab

        monkeypatch.setattr(KeysetGrab, "_get_device", staticmethod(lambda: None))
        grab = KeysetGrab([0x61])
        with grab:
            pass
        # After context exit, no grabs should be held.
        assert grab._grab_ids == []
