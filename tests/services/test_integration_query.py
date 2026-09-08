"""Tests for the read-only LAN query endpoint.

Covers GET /api/integration/control-novedades: multi-format factura
parsing, write-implies-read permission, and the por_factura shape.
"""

from unittest.mock import patch

from app.services.integration_service import (
    parse_factura_filter,
    query_by_facturas,
)

_READ_SESSION = {
    "ce_authenticated": True,
    "username": "ana",
    "rol": "validador",
    "permisos": ["control_urgencias"],
    "primer_nombre": "Ana",
    "segundo_nombre": "",
    "apellido_1": "Valdez",
    "apellido_2": "",
}

_RECORDS = [
    {"id": "1", "factura": "FEV1", "refactura": "", "observacion": "A"},
    {"id": "2", "factura": "FEV2", "refactura": "", "observacion": "B"},
    {"id": "3", "factura": "FEV9", "refactura": "FEV2", "observacion": "C"},
]


def _bearer_user(permisos):
    return {
        "id": 1,
        "username": "ana",
        "rol": "validador",
        "permisos": permisos,
        "primer_nombre": "Ana",
        "segundo_nombre": "",
        "apellido_1": "Valdez",
        "apellido_2": "",
    }


class TestParseFacturaFilter:
    def test_repeated_and_comma_params_merge(self):
        assert parse_factura_filter(["FEV1", "FEV2,FEV3"]) == [
            "FEV1",
            "FEV2",
            "FEV3",
        ]

    def test_normalizes_case_strips_and_dedupes(self):
        assert parse_factura_filter([" fev1 ", "FEV1", "fev2,, "]) == [
            "FEV1",
            "FEV2",
        ]

    def test_empty_input_returns_empty(self):
        assert parse_factura_filter(None) == []
        assert parse_factura_filter([]) == []


class TestQueryByFacturas:
    def test_shape_groups_and_reports_missing(self):
        with patch(
            "app.services.integration_service.get_errores",
            return_value={
                "status": "success",
                "data": {"errores": list(_RECORDS)},
                "errors": [],
            },
        ):
            envelope, status = query_by_facturas(["FEV1", "FEVX"], _READ_SESSION)
        assert status == 200
        assert envelope["status"] == "success"
        assert envelope["errors"] == []
        data = envelope["data"]
        assert data["facturas_solicitadas"] == ["FEV1", "FEVX"]
        assert data["no_encontradas"] == ["FEVX"]
        assert [r["id"] for r in data["por_factura"]["FEV1"]] == ["1"]
        assert data["por_factura"]["FEVX"] == []

    def test_single_factura_keeps_same_shape(self):
        with patch(
            "app.services.integration_service.get_errores",
            return_value={
                "status": "success",
                "data": {"errores": list(_RECORDS)},
                "errors": [],
            },
        ):
            envelope, status = query_by_facturas(["FEV2"], _READ_SESSION)
        assert status == 200
        por_factura = envelope["data"]["por_factura"]
        assert set(por_factura) == {"FEV2"}
        # Record 3 matches via refactura FEV2
        assert sorted(r["id"] for r in por_factura["FEV2"]) == ["2", "3"]
        assert envelope["data"]["no_encontradas"] == []

    def test_over_limit_returns_400(self):
        raw = [f"FEV{i}" for i in range(51)]
        envelope, status = query_by_facturas(raw, _READ_SESSION)
        assert status == 400
        assert envelope["status"] == "error"
        assert envelope["data"] == {}

    def test_no_filter_returns_all_grouped(self):
        with patch(
            "app.services.integration_service.get_errores",
            return_value={
                "status": "success",
                "data": {"errores": list(_RECORDS)},
                "errors": [],
            },
        ) as mock_get:
            envelope, status = query_by_facturas([], _READ_SESSION)
        assert status == 200
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs.get("facturas") is None
        assert envelope["data"]["facturas_solicitadas"] == []
        assert envelope["data"]["no_encontradas"] == []
        assert set(envelope["data"]["por_factura"]) == {"FEV1", "FEV2", "FEV9"}


class TestQueryRoutePermissions:
    def _get(self, app_client, query="", permisos=None):
        user = _bearer_user(
            ["control_urgencias:write"] if permisos is None else permisos
        )
        with (
            patch(
                "app.utils.token_store.get_user_for_token", return_value=user
            ),
            patch(
                "app.routes.integration.query_by_facturas",
                return_value=(
                    {
                        "status": "success",
                        "data": {
                            "facturas_solicitadas": [],
                            "no_encontradas": [],
                            "por_factura": {},
                        },
                        "errors": [],
                    },
                    200,
                ),
            ),
        ):
            return app_client.get(
                f"/api/integration/control-novedades{query}",
                headers={"Authorization": "Bearer valid-token"},
            )

    def test_write_permission_implies_read(self, app_client):
        resp = self._get(app_client, "?factura=FEV1")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"

    def test_base_permission_accepted(self, app_client):
        resp = self._get(app_client, "?factura=FEV1", ["control_urgencias"])
        assert resp.status_code == 200

    def test_admin_wildcard_accepted(self, app_client):
        resp = self._get(app_client, "?factura=FEV1", ["*"])
        assert resp.status_code == 200

    def test_unrelated_permission_denied(self, app_client):
        resp = self._get(app_client, "?factura=FEV1", ["procesar"])
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"

    def test_missing_token_returns_401(self, app_client):
        resp = app_client.get("/api/integration/control-novedades?factura=FEV1")
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"

    def test_comma_and_repeated_params_reach_service(self, app_client):
        user = _bearer_user(["control_urgencias:write"])
        with (
            patch(
                "app.utils.token_store.get_user_for_token", return_value=user
            ),
            patch(
                "app.routes.integration.query_by_facturas",
                return_value=(
                    {"status": "success", "data": {}, "errors": []},
                    200,
                ),
            ) as mock_query,
        ):
            resp = app_client.get(
                "/api/integration/control-novedades?factura=fev1,FEV2&factura=FEV3",
                headers={"Authorization": "Bearer valid-token"},
            )
        assert resp.status_code == 200
        assert mock_query.call_args.args[0] == ["fev1,FEV2", "FEV3"]
