"""Permission registry + :write expansion for the examenes module (UP-1/UP-4, EX-2).

Covers: ALLOWED_PERMISOS / PERMISO_MUTUAL_EXCLUSION / DASHBOARD_AREAS entries
(task 1.2), `:write` → base expansion at the API and shell level, and admin `*`
bypass for read and write endpoints.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.constants.base import (
    ALLOWED_PERMISOS,
    DASHBOARD_AREAS,
    PERMISO_MUTUAL_EXCLUSION,
)
from app.utils import examenes_store


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect store IO to tmp so tests never touch app/data."""
    monkeypatch.setattr(examenes_store, "DATA_DIR", tmp_path)


def _authenticate(client, permisos: list[str]) -> None:
    with client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "test"
        sess["permisos"] = permisos


class TestPermissionRegistry:
    """Task 1.2: base.py registry accepts examenes + examenes:write."""

    def test_allowed_permisos_include_examenes(self) -> None:
        assert "examenes" in ALLOWED_PERMISOS
        assert "examenes:write" in ALLOWED_PERMISOS

    def test_mutual_exclusion_pairs_examenes(self) -> None:
        assert PERMISO_MUTUAL_EXCLUSION["examenes"] == "examenes:write"
        assert PERMISO_MUTUAL_EXCLUSION["examenes:write"] == "examenes"

    def test_dashboard_area_card(self) -> None:
        """DASHBOARD_AREAS has an examenes card pointing at /examenes (UP-4)."""
        card = next(a for a in DASHBOARD_AREAS if a["href"] == "/examenes")
        assert card["permiso"] == "examenes"
        assert card["title"] == "Exámenes"


class TestWriteExpansion:
    """EX-2 expansion: `examenes:write` implies read access everywhere."""

    def test_write_user_can_get_catalog(self, app_client) -> None:
        """GET /api/examenes with only examenes:write → 200 (expansion)."""
        _authenticate(app_client, ["examenes:write"])

        response = app_client.get("/api/examenes")

        assert response.status_code == 200
        assert response.get_json()["status"] == "success"

    def test_write_user_can_get_listado(self, app_client) -> None:
        _authenticate(app_client, ["examenes:write"])
        assert app_client.get("/api/listado").status_code == 200

    def test_write_user_can_load_shell(self, app_client) -> None:
        """Shell route (requires `examenes`) accessible to :write user."""
        _authenticate(app_client, ["examenes:write"])
        assert app_client.get("/examenes").status_code == 200


class TestAdminBypass:
    """Admin (*) passes any permission gate (auth.py semantics)."""

    def test_admin_reads(self, app_client) -> None:
        _authenticate(app_client, ["*"])
        assert app_client.get("/api/examenes").status_code == 200
        assert app_client.get("/api/listado").status_code == 200

    def test_admin_writes(self, app_client) -> None:
        _authenticate(app_client, ["*"])
        response = app_client.post("/api/listado", json=[{"id": "pf-admin"}])
        assert response.status_code == 200
        assert response.get_json()["status"] == "success"