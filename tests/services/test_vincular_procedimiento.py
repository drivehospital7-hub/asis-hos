"""Tests for POST /api/eps/<id>/vincular-procedimiento.

Strict TDD — tests written before implementation.
Covers tasks 1.1, 1.2, 4.1.
"""

from __future__ import annotations

import json
import time

import pytest


class TestVincularProcedimientoIntegration:
    """Integration tests for the compound endpoint."""

    @pytest.fixture(autouse=True)
    def setup_data(self, app_client, request):
        """Create test EPS, NotaHoja, and Procedimiento with unique names."""
        # Login
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})

        tag = f"V{int(time.time() * 1000000) % 10000000}"

        # Create EPS
        eps_data = {"cod_contrato": f"{tag}_EPS", "eps": f"EPS {tag}", "regimen": "SUBSIDIADO"}
        resp = app_client.post(
            "/api/eps",
            data=json.dumps(eps_data),
            content_type="application/json",
        )
        assert resp.status_code == 201, f"Setup EPS failed: {resp.get_json()}"
        self._eps = resp.get_json()["data"]

        # Create NotaHoja
        nh_data = {"nota": f"NOTA {tag}"}
        resp = app_client.post(
            "/api/notas-hoja",
            data=json.dumps(nh_data),
            content_type="application/json",
        )
        assert resp.status_code == 201, f"Setup NotaHoja failed: {resp.get_json()}"
        self._nh = resp.get_json()["data"]

        # Create Procedimiento
        proc_data = {"cups": f"{tag[-4:]}", "procedimiento": f"PROC {tag}"}
        resp = app_client.post(
            "/api/procedimientos",
            data=json.dumps(proc_data),
            content_type="application/json",
        )
        assert resp.status_code == 201, f"Setup Procedimiento failed: {resp.get_json()}"
        self._proc = resp.get_json()["data"]

    # ─── Helper ───────────────────────────────────────────────────────

    def _vincular(self, app_client, eps_id, **kwargs):
        """Helper to call the vincular endpoint."""
        body = {
            "id_nota_hoja": kwargs.get("id_nota_hoja", self._nh["id"]),
            "id_procedimiento": kwargs.get("id_procedimiento", self._proc["id"]),
            "tarifa": kwargs.get("tarifa", 45000.00),
        }
        # Override with raw values for type testing
        for key in ("id_nota_hoja", "id_procedimiento", "tarifa"):
            raw_key = f"{key}_raw"
            if raw_key in kwargs:
                body[key] = kwargs[raw_key]

        return app_client.post(
            f"/api/eps/{eps_id}/vincular-procedimiento",
            data=json.dumps(body),
            content_type="application/json",
        )

    # ─── Happy path ───────────────────────────────────────────────────

    def test_happy_path_returns_201(self, app_client):
        """Valid vincular returns 201 and both rows created."""
        resp = self._vincular(app_client, self._eps["id"])
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.get_json()}"

        data = resp.get_json()
        assert data["status"] == "success"
        assert "eps_nota" in data["data"]
        assert "notas_tecnicas" in data["data"]

        en = data["data"]["eps_nota"]
        assert en["id_nota_hoja"] == self._nh["id"]
        assert en["id_eps_contratado"] == self._eps["id"]

        nt = data["data"]["notas_tecnicas"]
        assert nt["id_procedimiento"] == self._proc["id"]
        assert nt["id_nota_hoja"] == self._nh["id"]
        assert nt["tarifa"] == 45000.00

    def test_happy_path_links_same_id_nota_hoja(self, app_client):
        """Both EpsNota and NotasTecnicas share the same id_nota_hoja."""
        resp = self._vincular(app_client, self._eps["id"])
        assert resp.status_code == 201

        data = resp.get_json()["data"]
        assert data["eps_nota"]["id_nota_hoja"] == data["notas_tecnicas"]["id_nota_hoja"]

    # ─── Duplicate ────────────────────────────────────────────────────

    def test_duplicate_eps_nota_returns_400(self, app_client):
        """Same (id_nota_hoja, eps) combination returns 400."""
        # First vincular succeeds
        resp1 = self._vincular(app_client, self._eps["id"])
        assert resp1.status_code == 201

        # Second vincular with same combo fails
        resp2 = self._vincular(app_client, self._eps["id"])
        assert resp2.status_code == 400
        data = resp2.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0

    # ─── Missing fields ──────────────────────────────────────────────

    def test_missing_id_nota_hoja_returns_400(self, app_client):
        """Missing id_nota_hoja returns 400."""
        body = {"id_procedimiento": self._proc["id"], "tarifa": 45000}
        resp = app_client.post(
            f"/api/eps/{self._eps['id']}/vincular-procedimiento",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    def test_missing_id_procedimiento_returns_400(self, app_client):
        """Missing id_procedimiento returns 400."""
        body = {"id_nota_hoja": self._nh["id"], "tarifa": 45000}
        resp = app_client.post(
            f"/api/eps/{self._eps['id']}/vincular-procedimiento",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    def test_missing_tarifa_returns_400(self, app_client):
        """Missing tarifa returns 400."""
        body = {"id_nota_hoja": self._nh["id"], "id_procedimiento": self._proc["id"]}
        resp = app_client.post(
            f"/api/eps/{self._eps['id']}/vincular-procedimiento",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    # ─── Bad tarifa ───────────────────────────────────────────────────

    def test_tarifa_zero_returns_400(self, app_client):
        """tarifa = 0 returns 400."""
        resp = self._vincular(app_client, self._eps["id"], tarifa=0)
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    def test_tarifa_negative_returns_400(self, app_client):
        """tarifa < 0 returns 400."""
        resp = self._vincular(app_client, self._eps["id"], tarifa=-100)
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    def test_tarifa_non_numeric_returns_400(self, app_client):
        """Non-numeric tarifa returns 400."""
        resp = self._vincular(app_client, self._eps["id"], tarifa_raw="abc")
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    # ─── EPS not found ────────────────────────────────────────────────

    def test_eps_not_found_returns_404(self, app_client):
        """Non-existent EPS ID returns 404."""
        resp = self._vincular(app_client, 99999)
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == "error"

    # ─── Entity validation ────────────────────────────────────────────

    def test_nonexistent_nota_hoja_returns_400(self, app_client):
        """Non-existent NotaHoja returns 400."""
        resp = self._vincular(app_client, self._eps["id"], id_nota_hoja=99999)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    def test_nonexistent_procedimiento_returns_400(self, app_client):
        """Non-existent Procedimiento returns 400."""
        resp = self._vincular(app_client, self._eps["id"], id_procedimiento=99999)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    # ─── Auth ─────────────────────────────────────────────────────────

    def test_requires_auth(self, app_client):
        """Unauthenticated request returns 401."""
        with app_client.session_transaction() as sess:
            sess.clear()

        resp = self._vincular(app_client, self._eps["id"])
        assert resp.status_code == 401
