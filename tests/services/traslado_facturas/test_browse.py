"""Tests for traslado browse_service: list_dirs."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.constants.monitoreo_carpetas import MOVE_ERR_TRAVERSAL
from app.services.traslado_facturas.browse_service import list_dirs


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "Juan" / "FEV001").mkdir(parents=True)
    (root / "Ana").mkdir(parents=True)
    (root / "Juan" / "file.txt").write_text("x")
    return root


class TestListDirs:
    def test_sin_path_lista_raices(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        data, error = list_dirs(None, [str(root)])
        assert error is None
        assert data == {
            "actual": None,
            "padre": None,
            "dirs": [{"name": str(root), "path": str(root)}],
        }

    def test_subdirs_no_recursivo_solo_nombres(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        data, error = list_dirs(str(root), [str(tmp_path)])
        assert error is None
        assert data["actual"] == str(root.resolve())
        assert data["padre"] == str(tmp_path.resolve())
        assert data["dirs"] == [
            {"name": "Ana", "path": str(root / "Ana")},
            {"name": "Juan", "path": str(root / "Juan")},
        ]

    def test_traversal_rechazado(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        data, error = list_dirs(str(root / ".." / "evil"), [str(root)])
        assert data is None
        assert error == MOVE_ERR_TRAVERSAL

    def test_fuera_de_roots_rechazado(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        data, error = list_dirs(str(outside), [str(root)])
        assert data is None
        assert error == MOVE_ERR_TRAVERSAL

    def test_relativo_rechazado(self, tmp_path: Path) -> None:
        data, error = list_dirs("relative/path", [str(tmp_path)])
        assert data is None
        assert error == MOVE_ERR_TRAVERSAL

    def test_inexistente_error(self, tmp_path: Path) -> None:
        data, error = list_dirs(str(tmp_path / "nope"), [str(tmp_path)])
        assert data is None
        assert error is not None

    def test_sin_roots_error(self, tmp_path: Path) -> None:
        data, error = list_dirs(str(tmp_path), [])
        assert data is None
        assert error is not None
