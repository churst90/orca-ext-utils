"""Tests for text_to_braille.

Pure-Python ASCII table -- liblouis path is mocked so the test
suite runs without the louis Python module installed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestAsciiTable:
    def test_empty_input_returns_empty(self):
        from orca_ext_utils.text_to_braille import text_to_cells

        assert text_to_cells("") == b""

    def test_letters_match_us_computer_braille(self):
        from orca_ext_utils.text_to_braille import text_to_cells

        # a = dot 1 = 0x01, b = dots 1,2 = 0x03, c = dots 1,4 = 0x09.
        assert text_to_cells("abc") == bytes([0x01, 0x03, 0x09])

    def test_digits_match_us_computer_braille(self):
        from orca_ext_utils.text_to_braille import text_to_cells

        # 1 = dot 2 = 0x02 in US computer braille.
        assert text_to_cells("1") == bytes([0x02])

    def test_unknown_chars_become_blank_cells(self):
        from orca_ext_utils.text_to_braille import text_to_cells

        # Non-ASCII Latin chars aren't in the table; should be 0.
        result = text_to_cells("aéb")  # 'a', 'é', 'b'
        assert result[1] == 0
        # And the position of 'b' is preserved (no shift from dropping
        # the unknown char).
        assert result == bytes([0x01, 0x00, 0x03])

    def test_space_renders_blank(self):
        from orca_ext_utils.text_to_braille import text_to_cells

        assert text_to_cells("a b") == bytes([0x01, 0x00, 0x03])


class TestUnicodeBraille:
    def test_returns_braille_pattern_codepoints(self):
        from orca_ext_utils.text_to_braille import text_to_unicode_braille

        result = text_to_unicode_braille("a")
        # 'a' = mask 0x01 -> U+2801.
        assert result == "⠁"

    def test_blanks_render_as_u2800(self):
        from orca_ext_utils.text_to_braille import text_to_unicode_braille

        # Unknown char -> blank cell -> U+2800.
        result = text_to_unicode_braille("\x00")
        assert result == "⠀"


class TestBackends:
    def test_ascii_always_available(self):
        from orca_ext_utils.text_to_braille import available_backends

        assert "ascii" in available_backends()

    def test_liblouis_present_when_louis_imports(self, monkeypatch):
        from orca_ext_utils import text_to_braille

        # Reset the lru_cache so our monkeypatch takes effect.
        text_to_braille._liblouis_available.cache_clear()
        fake_louis = mock.Mock()
        monkeypatch.setitem(sys.modules, "louis", fake_louis)
        try:
            assert "liblouis" in text_to_braille.available_backends()
        finally:
            sys.modules.pop("louis", None)
            text_to_braille._liblouis_available.cache_clear()

    def test_liblouis_absent_when_louis_missing(self, monkeypatch):
        from orca_ext_utils import text_to_braille

        text_to_braille._liblouis_available.cache_clear()
        # Ensure louis is not in sys.modules so the import fails.
        sys.modules.pop("louis", None)
        # Hide louis from finders.
        monkeypatch.setitem(
            sys.modules, "louis",
            None,  # None makes `import louis` raise ImportError.
        )
        try:
            assert "liblouis" not in text_to_braille.available_backends()
        finally:
            sys.modules.pop("louis", None)
            text_to_braille._liblouis_available.cache_clear()


class TestTableArgument:
    def test_no_table_uses_ascii_only(self, monkeypatch):
        # Even if louis is fake-present, table=None skips it.
        from orca_ext_utils import text_to_braille

        text_to_braille._liblouis_available.cache_clear()
        fake_louis = mock.Mock()
        fake_louis.translateString = mock.Mock(
            side_effect=RuntimeError("should not be called"),
        )
        monkeypatch.setitem(sys.modules, "louis", fake_louis)
        try:
            result = text_to_braille.text_to_cells("a", table=None)
            assert result == bytes([0x01])
        finally:
            sys.modules.pop("louis", None)
            text_to_braille._liblouis_available.cache_clear()

    def test_liblouis_failure_falls_back_to_ascii(self, monkeypatch):
        from orca_ext_utils import text_to_braille

        text_to_braille._liblouis_available.cache_clear()
        fake_louis = mock.Mock()
        fake_louis.translateString = mock.Mock(side_effect=RuntimeError("boom"))
        monkeypatch.setitem(sys.modules, "louis", fake_louis)
        try:
            result = text_to_braille.text_to_cells("a", table="any.ctb")
            # Should fall back to ASCII table cleanly.
            assert result == bytes([0x01])
        finally:
            sys.modules.pop("louis", None)
            text_to_braille._liblouis_available.cache_clear()
