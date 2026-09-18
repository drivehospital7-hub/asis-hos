"""RED tests for POST /monitoreo-carpetas/move route (monitoreo-mover-facturas).

Strict TDD: route does not exist yet — these MUST fail (404) until GREEN.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _auth(app_client, permisos) -> None:
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "test"
        sess["permisos"] = permisos


class TestMoveRoute:
    def test_requires_write_perm_403_moves_nothing(
        self, app_client, tmp_path: Path
    ) -> None:
        src = tmp_path / "FEV001"
        src.mkdir(parents=True)
        (src / "dummy.txt").write_text("x")
        dest = tmp_path / "dest"
        dest.mkdir()
        _auth(app_client, ["monitoreo_carpetas"])  # read-only, no :write
        resp = app_client.post(
            "/monitoreo-carpetas/move",
            json={"sources": [str(src)], "dest_dir": str(dest)},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        # nothing moved
        assert src.exists()
        assert not (dest / "FEV001").exists()

    def test_over_limit_422_moves_nothing(self, app_client, tmp_path: Path) -> None:
        from app.constants.monitoreo_carpetas import MOVE_MAX_BATCH

        src = tmp_path / "src"
        src.mkdir(parents=True)
        (src / "FEV001").mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()
        _auth(app_client, ["*"])
        os.environ["MONITOREO_CARPETAS_ROOTS"] = json.dumps([str(tmp_path)])
        try:
            sources = [str(src / f"F{i:03d}") for i in range(MOVE_MAX_BATCH + 1)]
            resp = app_client.post(
                "/monitoreo-carpetas/move",
                json={"sources": sources, "dest_dir": str(dest)},
            )
            assert resp.status_code == 422
            data = resp.get_json()
            assert data["status"] == "error"
        finally:
            os.environ.pop("MONITOREO_CARPETAS_ROOTS", None)

    def test_authorized_move_returns_envelope(self, app_client, tmp_path: Path) -> None:
        src = tmp_path / "src"
        (src / "FEV001").mkdir(parents=True)
        (src / "FEV001" / "dummy.txt").write_text("x")
        dest = tmp_path / "dest"
        dest.mkdir()
        _auth(app_client, ["*"])
        os.environ["MONITOREO_CARPETAS_ROOTS"] = json.dumps([str(tmp_path)])
        try:
            resp = app_client.post(
                "/monitoreo-carpetas/move",
                json={"sources": [str(src / "FEV001")], "dest_dir": str(dest)},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"
            assert "moved" in data["data"]
            assert "failed" in data["data"]
            assert len(data["data"]["moved"]) == 1
        finally:
            os.environ.pop("MONITOREO_CARPETAS_ROOTS", None)
