"""Tests for extension_settings JSON backend.

GSettings path is unit-tested via the backend() probe; the
JSON-backed paths get real disk I/O against a tmp_path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestJsonBackend:
    def test_get_returns_default_for_unset_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        assert s.get("absent_key") is None
        assert s.get("absent_key", default="fallback") == "fallback"

    def test_set_and_get_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        assert s.set("name", "Cody") is True
        # New Settings instance to verify persistence (don't trust cache).
        s2 = Settings("test_ext")
        assert s2.get("name") == "Cody"

    def test_set_various_types(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        assert s.set("flag", True) is True
        assert s.set("count", 42) is True
        assert s.set("ratio", 3.14) is True
        assert s.set("tags", ["a", "b", "c"]) is True
        assert s.set("nested", {"k": "v", "n": 1}) is True

        s2 = Settings("test_ext")
        assert s2.get("flag") is True
        assert s2.get("count") == 42
        assert s2.get("ratio") == 3.14
        assert s2.get("tags") == ["a", "b", "c"]
        assert s2.get("nested") == {"k": "v", "n": 1}

    def test_unserializable_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings
        import pytest

        s = Settings("test_ext")

        class Custom:
            pass

        with pytest.raises(ValueError):
            s.set("obj", Custom())

    def test_delete_removes_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        s.set("temp", "value")
        assert s.delete("temp") is True
        s2 = Settings("test_ext")
        assert s2.get("temp") is None

    def test_delete_returns_false_for_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        assert s.delete("never_set") is False

    def test_defaults_dict_returned_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext", defaults={"language": "en", "verbose": False})
        assert s.get("language") == "en"
        assert s.get("verbose") is False
        # Instance default ("en") wins over explicit default arg
        # ("es") because the instance default is the library author's
        # declared meaning; the explicit arg is the caller's "if
        # nothing's known" fallback.
        assert s.get("language", default="es") == "en"
        # For a key with no instance default, explicit arg is used.
        assert s.get("missing_key", default="fallback") == "fallback"

    def test_set_overrides_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext", defaults={"language": "en"})
        s.set("language", "es")
        # New instance + same defaults: stored value wins over default.
        s2 = Settings("test_ext", defaults={"language": "en"})
        assert s2.get("language") == "es"

    def test_keys_returns_set_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext", defaults={"unset_default": "x"})
        s.set("a", 1)
        s.set("b", 2)
        # Defaults that haven't been overridden aren't in keys().
        assert sorted(s.keys()) == ["a", "b"]


class TestBackendDetection:
    def test_backend_returns_json_without_schema(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        # No GSettings schema for "test_ext_no_schema" should exist
        # in any normal test environment.
        s = Settings("test_ext_no_schema")
        assert s.backend() == "json"


class TestAtomicWrite:
    def test_write_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        s.set("k", "v")
        # The orca/extensions/ subdir should exist now.
        expected = tmp_path / "orca" / "extensions" / "test_ext.json"
        assert expected.exists()
        # And contain valid JSON.
        data = json.loads(expected.read_text())
        assert data == {"k": "v"}

    def test_no_temp_files_left_after_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        from orca_ext_utils.extension_settings import Settings

        s = Settings("test_ext")
        s.set("k", "v")
        ext_dir = tmp_path / "orca" / "extensions"
        # Only the actual file should be present; no .tmp leftovers.
        files = list(ext_dir.iterdir())
        assert len(files) == 1
        assert files[0].name == "test_ext.json"
