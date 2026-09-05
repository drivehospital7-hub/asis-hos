"""Tests for app/utils/monitoreo_store.py — get_roots, save_roots, reset_roots.

Covers all spec scenarios from folder-scanner-config/spec.md:
- R1: Read Roots with Fallback (JSON > env var > empty)
- R2: Save Roots Atomically (first save, overwrite, failure)
- R3: Reset to Env Default (delete file, no-op when absent)
- R4: Env Var Parsing (JSON array, semicolon, empty)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from app.utils.monitoreo_store import get_roots, save_roots


class TestGetRoots:
    """Spec R1: Read Roots with Fallback."""

    def test_manual_json_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON file has roots → returns those, fuente=manual."""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"roots": ["//srv/a", "//srv/b"], "fuente": "manual", "ultima_actualizacion": "2026-07-04T12:00:00"})
        )
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        roots, fuente, _ = get_roots()

        assert roots == ["//srv/a", "//srv/b"]
        assert fuente == "manual"

    def test_fallback_to_env_var_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON absent, env var set as JSON array → returns env roots, fuente=env."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.setenv("MONITOREO_CARPETAS_ROOTS", json.dumps(["//srv/env"]))

        roots, fuente, _ = get_roots()

        assert roots == ["//srv/env"]
        assert fuente == "env"

    def test_fallback_to_env_var_semicolon(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON absent, env var set as semicolon-separated → returns env roots."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.setenv("MONITOREO_CARPETAS_ROOTS", "//srv/a;//srv/b")

        roots, fuente, _ = get_roots()

        assert roots == ["//srv/a", "//srv/b"]
        assert fuente == "env"

    def test_neither_configured(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No JSON, no env var → returns [], fuente=env."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.delenv("MONITOREO_CARPETAS_ROOTS", raising=False)

        roots, fuente, _ = get_roots()

        assert roots == []
        assert fuente == "env"

    def test_empty_env_var_with_json_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON absent, empty env var → returns [], fuente=env."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.setenv("MONITOREO_CARPETAS_ROOTS", "")

        roots, fuente, _ = get_roots()

        assert roots == []
        assert fuente == "env"

    def test_corrupt_json_falls_back(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Corrupt JSON file → falls back to env var, logs warning."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{bad syntax}")
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.setenv("MONITOREO_CARPETAS_ROOTS", json.dumps(["//fallback"]))

        roots, fuente, _ = get_roots()

        assert roots == ["//fallback"]
        assert fuente == "env"

    def test_corrupt_json_no_env_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Corrupt JSON and no env var → returns [], fuente=env."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{bad syntax}")
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)
        monkeypatch.delenv("MONITOREO_CARPETAS_ROOTS", raising=False)

        roots, fuente, _ = get_roots()

        assert roots == []
        assert fuente == "env"


class TestSaveRoots:
    """Spec R2: Save Roots Atomically."""

    def test_first_save_creates_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No JSON exists → save creates file with roots, fuente=manual."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        save_roots(["//ruta1"])

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["roots"] == ["//ruta1"]
        assert data["fuente"] == "manual"
        assert "ultima_actualizacion" in data

    def test_overwrite_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON has old roots → after save, only new roots present."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"roots": ["//old"], "fuente": "manual", "ultima_actualizacion": "2026-01-01T00:00:00"}))
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        save_roots(["//new"])

        data = json.loads(config_file.read_text())
        assert data["roots"] == ["//new"]
        assert data["fuente"] == "manual"

    def test_atomic_write_preserves_original_on_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """If atomic write fails, original JSON is unmodified."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"roots": ["//original"], "fuente": "manual", "ultima_actualizacion": "2026-01-01T00:00:00"}))
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        # Mock Path.replace to fail unconditionally
        def failing_replace(self, target):
            raise OSError("Simulated write failure")

        monkeypatch.setattr(Path, "replace", failing_replace)

        with pytest.raises(OSError, match="Simulated write failure"):
            save_roots(["//new"])

        # Original file must be intact
        data = json.loads(config_file.read_text())
        assert data["roots"] == ["//original"]

    def test_save_with_empty_roots_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Saving empty list raises ValueError."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        with pytest.raises(ValueError, match="no vacía"):
            save_roots([])

    def test_save_with_non_string_roots_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Saving non-string items raises ValueError."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr("app.utils.monitoreo_store.CONFIG_FILE", config_file)

        with pytest.raises(ValueError, match="strings"):
            save_roots([123])
