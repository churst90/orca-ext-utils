"""Tests for key_combo_helpers.

Pure-Python paths -- Gdk fallback paths are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestParseChord:
    def test_single_key(self):
        from orca_ext_utils.key_combo_helpers import parse_chord

        assert parse_chord("a") == (0, 0x61)

    def test_ctrl_letter(self):
        from orca_ext_utils.key_combo_helpers import parse_chord, MOD_CTRL

        assert parse_chord("Ctrl+a") == (MOD_CTRL, 0x61)

    def test_multiple_modifiers(self):
        from orca_ext_utils.key_combo_helpers import (
            parse_chord, MOD_CTRL, MOD_SHIFT, MOD_ALT,
        )

        mask, keysym = parse_chord("Ctrl+Shift+Alt+a")
        assert mask == (MOD_CTRL | MOD_SHIFT | MOD_ALT)
        assert keysym == 0x61

    def test_aliases_accepted(self):
        from orca_ext_utils.key_combo_helpers import parse_chord, MOD_CTRL, MOD_SUPER

        # "control" / "ctl" / "^" should all parse as Ctrl.
        for alias in ("control", "ctl", "^", "CTRL"):
            mask, _ = parse_chord(f"{alias}+a")
            assert mask == MOD_CTRL, f"alias {alias} failed"
        # "win" / "windows" / "cmd" should parse as Super.
        for alias in ("win", "windows", "cmd", "Super"):
            mask, _ = parse_chord(f"{alias}+a")
            assert mask == MOD_SUPER, f"alias {alias} failed"

    def test_named_keys(self):
        from orca_ext_utils.key_combo_helpers import parse_chord

        _, keysym = parse_chord("Up")
        assert keysym == 0xff52
        _, keysym = parse_chord("Escape")
        assert keysym == 0xff1b
        _, keysym = parse_chord("F1")
        assert keysym == 0xffbe

    def test_unknown_key_returns_zero(self):
        from orca_ext_utils.key_combo_helpers import parse_chord

        # Unknown key name -> (0, 0).
        assert parse_chord("Ctrl+SomeFakeKey") == (0, 0)

    def test_empty_returns_zero(self):
        from orca_ext_utils.key_combo_helpers import parse_chord

        assert parse_chord("") == (0, 0)

    def test_whitespace_separators(self):
        from orca_ext_utils.key_combo_helpers import parse_chord, MOD_CTRL

        # Tolerate "Ctrl + a" with whitespace.
        assert parse_chord("Ctrl + a") == (MOD_CTRL, 0x61)


class TestFormatChord:
    def test_single_letter(self):
        from orca_ext_utils.key_combo_helpers import format_chord

        assert format_chord(0, 0x61) == "a"

    def test_ctrl_letter(self):
        from orca_ext_utils.key_combo_helpers import format_chord

        assert format_chord(0x04, 0x61) == "Ctrl+a"

    def test_canonical_modifier_order(self):
        from orca_ext_utils.key_combo_helpers import format_chord, MOD_CTRL, MOD_ALT, MOD_SHIFT

        # Order in output is always Ctrl, Alt, Shift, Super --
        # regardless of how the mask was built up.
        assert format_chord(MOD_SHIFT | MOD_ALT | MOD_CTRL, 0x61) == "Ctrl+Alt+Shift+a"

    def test_unknown_keysym_renders_as_hex(self):
        from orca_ext_utils.key_combo_helpers import format_chord

        # 0xabcd isn't in our table; render as hex.
        # Single-token tail with no display name.
        result = format_chord(0, 0xabcd)
        assert result.endswith("0xabcd")

    def test_named_key_title_cased(self):
        from orca_ext_utils.key_combo_helpers import format_chord

        # "up" in our table becomes "Up" in output.
        assert format_chord(0, 0xff52) == "Up"


class TestRoundTrip:
    def test_parse_format_roundtrip(self):
        from orca_ext_utils.key_combo_helpers import parse_chord, format_chord

        cases = ["a", "Ctrl+a", "Ctrl+Shift+Up", "Alt+F1", "Escape"]
        for chord in cases:
            mask, keysym = parse_chord(chord)
            reconstructed = format_chord(mask, keysym)
            # Re-parse the reconstruction to verify equivalence
            # (string equality could fail on capitalization without
            # losing information).
            assert parse_chord(reconstructed) == (mask, keysym), \
                f"roundtrip failed for {chord!r}"


class TestModifierNames:
    def test_no_modifiers_empty(self):
        from orca_ext_utils.key_combo_helpers import modifier_names

        assert modifier_names(0) == ()

    def test_all_named_modifiers(self):
        from orca_ext_utils.key_combo_helpers import (
            modifier_names, MOD_CTRL, MOD_ALT, MOD_SHIFT, MOD_SUPER,
        )

        names = modifier_names(MOD_CTRL | MOD_ALT | MOD_SHIFT | MOD_SUPER)
        assert names == ("Ctrl", "Alt", "Shift", "Super")

    def test_unnamed_bits_dropped(self):
        from orca_ext_utils.key_combo_helpers import modifier_names, MOD_CTRL

        # Bit 0x10 (Mod2) has no canonical name; should be dropped silently.
        assert modifier_names(MOD_CTRL | 0x10) == ("Ctrl",)


class TestNameToKeysym:
    def test_hex_form(self):
        from orca_ext_utils.key_combo_helpers import name_to_keysym

        assert name_to_keysym("0xff1b") == 0xff1b

    def test_unknown_no_display(self):
        from orca_ext_utils.key_combo_helpers import name_to_keysym

        # In a typical test env Gdk fallback returns 0 for fake names.
        assert name_to_keysym("definitely_not_a_real_key_name") == 0
