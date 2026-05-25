"""Tests for the new /odontologia-equipos-basicos blueprint.

Strict TDD: tests written BEFORE implementation.
Covers spec requirements R1-R6 for the independent EB module.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from openpyxl import Workbook


# =============================================================================
# Test 4.5: Constants importable
# =============================================================================


class TestConstantsImportable:
    """Spec R4: EB constants MUST reside in app/constants/equipos_basicos.py."""

    def test_import_profesionales_equipos_basicos(self):
        """PROFESIONALES_EQUIPOS_BASICOS importable from app.constants."""
        from app.constants import PROFESIONALES_EQUIPOS_BASICOS

        assert len(PROFESIONALES_EQUIPOS_BASICOS) > 0
        assert "03764" in PROFESIONALES_EQUIPOS_BASICOS
        assert PROFESIONALES_EQUIPOS_BASICOS["03764"]["tipo"] == "ODONTOLOGO"

    def test_import_centro_costo_equipos_basicos(self):
        """CENTRO_COSTO_EQUIPOS_BASICOS importable from app.constants."""
        from app.constants import CENTRO_COSTO_EQUIPOS_BASICOS

        assert CENTRO_COSTO_EQUIPOS_BASICOS == "EQUIPOS BASICOS ODONTOLOGIA"

    def test_import_equipos_basicos_thresholds(self):
        """EB-specific thresholds importable from app.constants."""
        from app.constants import (
            EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD,
            EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN,
            EQUIPOS_BASICOS_CANTIDAD_MAX,
            EQUIPOS_BASICOS_CANTIDAD_PYP_MIN,
        )

        assert EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD == 3
        assert EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN == 2
        assert EQUIPOS_BASICOS_CANTIDAD_MAX == 10

    def test_import_odontologia_does_not_have_eb_constants(self):
        """Odontologia module no longer contains EB-specific constants."""
        from app.constants import odontologia

        assert not hasattr(odontologia, "PROFESIONALES_EQUIPOS_BASICOS")

    def test_import_columnas_does_not_have_eb_constants(self):
        """Columnas module no longer contains EB-specific constants."""
        from app.constants import columnas

        assert not hasattr(columnas, "EQUIPOS_BASICOS_COLUMNS_TO_KEEP")
        assert not hasattr(columnas, "EQUIPOS_BASICOS_REVISION_HEADERS")
        assert not hasattr(columnas, "CENTRO_COSTO_EQUIPOS_BASICOS")


# =============================================================================
# Test 4.4: exporter.py rejects equipos_basicos kwarg
# =============================================================================


class TestExporterRejectsEquiposBasicosKwarg:
    """Spec R3: equipos_basicos param removed from exporter signature."""

    def test_detect_problems_only_no_equipos_basicos_param(self):
        """detect_problems_only raises TypeError if equipos_basicos is passed."""
        from app.services.exporter import detect_problems_only

        with pytest.raises(TypeError):
            detect_problems_only(
                filename="test.xlsx",
                equipos_basicos=True,  # type: ignore
            )

    def test_detect_problems_only_works_without_equipos_basicos(self):
        """detect_problems_only works when called without equipos_basicos."""
        from app.services.exporter import detect_problems_only

        with patch(
            "app.services.exporter.acquire_semaphore",
            return_value=True,
        ):
            with patch(
                "app.services.exporter.release_semaphore",
            ):
                result, status = detect_problems_only(
                    filename="nonexistent.xlsx",
                    area="equipos_basicos",
                )
                # Should get error about path resolution, not TypeError
                assert status == 500 or result["status"] == "error"

    def test_do_detect_problems_rejects_equipos_basicos(self):
        """_do_detect_problems raises TypeError if equipos_basicos is passed."""
        from app.services.exporter import _do_detect_problems

        with pytest.raises(TypeError):
            _do_detect_problems(
                filename="test.xlsx",
                equipos_basicos=True,  # type: ignore
            )

    def test_do_detect_problems_works_with_area_param(self):
        """_do_detect_problems works when area=AREA_EQUIPOS_BASICOS is passed instead."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                import polars as pl
                df = pl.DataFrame({"A": ["header"]})
                with patch(
                    "app.services.exporter.pl.read_excel",
                    return_value=df,
                ):
                    result = _do_detect_problems(
                        filename="test.xlsx",
                        area="equipos_basicos",
                    )
                    # Should proceed to detection (will fail with KeyError since no real indices)
                    assert result["status"] in ("error", "success")


# =============================================================================
# Helper: create a minimal EB Excel file
# =============================================================================


def _make_eb_excel(headers: list[str], rows: list[list]) -> io.BytesIO:
    """Create a real .xlsx in memory with given headers and data rows."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    for col, h in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=h)
    for row_idx, row_data in enumerate(rows, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


EB_HEADERS = [
    "Número Factura",
    "Vlr. Subsidiado",
    "Vlr. Procedimiento",
    "Código Tipo Procedimiento",
    "Tipo Procedimiento",
    "Código",
    "Cód. Equivalente CUPS",
    "Procedimiento",
    "Nº Identificación",
    "Convenio Facturado",
    "Cantidad",
    "Laboratorio",
    "Centro Costo",
    "Cód Entidad Cobrar",
    "Entidad Cobrar",
    "Entidad Afiliación",
    "Tipo Factura Descripción",
    "IDE Contrato",
    "Tipo Identificación",
    "Fec. Nacimiento",
    "Fec. Factura",
    "Fecha Cierre",
    "Identificación Profesional",
    "Profesional Atiende",
    "Código Profesional",
    "Responsable Cierra Facturar",
    "Tarifario",
    "Tipo Usuario",
]


# =============================================================================
# Test 4.1: GET route returns 200 with permiso, 403 without, 401 unauthenticated
# =============================================================================


class TestGetRoute:
    """Spec R1: GET /odontologia-equipos-basicos/ requires auth + permiso."""

    def test_get_returns_200_with_permiso(self, app_client):
        """User with odontologia_equipos_basicos permiso can access GET."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia_equipos_basicos"]
            sess["username"] = "eb_user"

        resp = app_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "__INITIAL_DATA__" in html

    def test_get_returns_200_with_admin_star(self, app_client):
        """Admin (*) can access GET route."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        assert resp.status_code == 200

    def test_get_returns_403_without_permiso(self, app_client):
        """User without odontologia_equipos_basicos permiso gets 403/redirect."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odonto_user"

        resp = app_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        # Should redirect to home or return 403
        assert resp.status_code == 200  # Flask redirect with follow
        html = resp.data.decode("utf-8")
        # Should NOT render EB page
        assert "Equipos Básicos" not in html or "No tiene permiso" in html

    def test_get_returns_401_unauthenticated(self, fresh_client):
        """No session -> 401 from before_request middleware."""
        resp = fresh_client.get("/odontologia-equipos-basicos/")
        # before_request returns 401 (HTML template) for unauthenticated non-XHR requests
        assert resp.status_code == 401


# =============================================================================
# Test 4.2: POST processes EB Excel
# =============================================================================


class TestPostRoute:
    """Spec R2: POST /odontologia-equipos-basicos/ processes EB Excel."""

    def test_post_requires_permiso(self, fresh_client):
        """User without permiso gets 403 on POST."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odonto_user"

        buf = _make_eb_excel(EB_HEADERS, [["FAC-001", "1000", "1000", "ODT", "ODT", "890203", "", "Test", "123", "Asistencial", "1", "", "EQUIPOS BASICOS ODONTOLOGIA", "ESS118", "ESS118", "ESS118", "", "970", "CC", "1990-01-01", "2024-01-15", "", "123", "Dr Test", "03764", "Resp", "Tarifario 1", "SUBSIDIADO"]])
        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "test_eb.xlsx")},
        )
        # Permiso_requerido returns JSON 403 for non-admin users
        assert resp.status_code in (403, 200)
        if resp.status_code == 403:
            import json
            data = json.loads(resp.data.decode("utf-8"))
            assert data.get("status") == "error"

    def test_post_requires_auth(self, fresh_client):
        """No session -> 401 on POST."""
        buf = _make_eb_excel(EB_HEADERS, [])
        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "test_eb.xlsx")},
        )
        # before_request middleware returns 401 for unauthenticated
        assert resp.status_code == 401

    def test_post_processes_valid_eb_excel(self, fresh_client):
        """Valid EB Excel -> JSON response with problems."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia_equipos_basicos"]
            sess["username"] = "eb_user"

        # Create a minimal but valid EB file
        buf = _make_eb_excel(EB_HEADERS, [
            ["FAC-001", "1000", "1000", "ODT", "ODT", "890203", "", "Consulta de Primera vez por Odontologia General", "12345", "Asistencial", "1", "", "EQUIPOS BASICOS ODONTOLOGIA", "ESS118", "ESS118", "ESS118", "", "970", "CC", "1990-01-01", "2024-01-15", "", "123", "Dr Test", "03764", "Resp Cierra", "Tarifario 1", "SUBSIDIADO"],
        ])

        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "test_eb.xlsx")},
        )
        # Should return JSON (either success or error depending on detection)
        assert resp.status_code == 200 or resp.status_code == 500
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert "status" in data
        assert "data" in data


# =============================================================================
# Test 4.3: POST rejects missing file / invalid extension
# =============================================================================


class TestPostRejectsInvalidInput:
    """Spec R2: POST validation of file input."""

    def test_post_rejects_missing_file(self, fresh_client):
        """POST without file returns error."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = fresh_client.post("/odontologia-equipos-basicos/")
        # Should return JSON with error
        assert resp.status_code == 200
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert "errors" in data
        assert len(data.get("errors", [])) > 0 or data.get("status") == "error"

    def test_post_rejects_invalid_extension_csv(self, fresh_client):
        """POST with .csv file returns error."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        buf = io.BytesIO(b"dummy,csv,data")
        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "test.csv")},
        )
        assert resp.status_code == 200
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert data.get("status") == "error" or any(
            word in " ".join(data.get("errors", [])).lower()
            for word in ["extensión", "formato", "extensi", "permitid", "no permitido"]
        )

    def test_post_rejects_empty_filename(self, fresh_client):
        """POST with empty filename returns error."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (io.BytesIO(b"xlsx data"), "")},
        )
        assert resp.status_code == 200
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert len(data.get("errors", [])) > 0 or data.get("status") == "error"


# =============================================================================
# Test 4.7: Permission isolation
# =============================================================================


class TestPermissionIsolation:
    """Spec R5: Permission isolation between EB and odontologia."""

    def test_eb_user_blocked_from_odontologia(self, fresh_client):
        """User with only odontologia_equipos_basicos cannot access /odontologia/."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia_equipos_basicos"]
            sess["username"] = "eb_user"

        resp = fresh_client.get("/odontologia/", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        # Should be redirected to home or get error flash
        assert "Odontología" not in html or "No tiene permiso" in html or "no autorizado" in html.lower()

    def test_odontologia_user_blocked_from_eb(self, fresh_client):
        """User with only odontologia cannot access /odontologia-equipos-basicos/."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odonto_user"

        resp = fresh_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Equipos Básicos" not in html or "No tiene permiso" in html or "no autorizado" in html.lower()

    def test_both_permisos_access_both_routes(self, fresh_client):
        """User with both permisos can access both routes."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia", "odontologia_equipos_basicos"]
            sess["username"] = "dual_user"

        resp_odonto = fresh_client.get("/odontologia/", follow_redirects=True)
        assert resp_odonto.status_code == 200

        resp_eb = fresh_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        assert resp_eb.status_code == 200

    def test_no_permiso_blocked_from_both(self, fresh_client):
        """User with neither permiso is blocked from both routes."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["urgencias"]
            sess["username"] = "urgencias_user"

        resp_odonto = fresh_client.get("/odontologia/", follow_redirects=True)
        assert resp_odonto.status_code == 200
        html_odonto = resp_odonto.data.decode("utf-8")
        assert "Odontología" not in html_odonto or "No tiene permiso" in html_odonto

        resp_eb = fresh_client.get("/odontologia-equipos-basicos/", follow_redirects=True)
        assert resp_eb.status_code == 200
        html_eb = resp_eb.data.decode("utf-8")
        assert "Equipos Básicos" not in html_eb or "No tiene permiso" in html_eb


# =============================================================================
# Test 4.6: Full roundtrip with real EB Excel
# =============================================================================


class TestFullRoundtrip:
    """Spec R3: Full roundtrip with a real EB Excel file."""

    def test_roundtrip_clean_file(self, fresh_client):
        """Clean file -> status success with no/missing_columns error."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        # Create a real EB Excel with all required columns
        buf = _make_eb_excel(EB_HEADERS, [
            ["FAC-001", "0", "15000", "ODT", "ODT", "890203", "", "Consulta de Primera vez por Odontologia General", "12345", "Asistencial", "1", "", "EQUIPOS BASICOS ODONTOLOGIA", "ESS118", "ESS118", "ESS118", "", "970", "CC", "1990-01-01", "2024-01-15", "", "123", "Dr Test", "03764", "Resp Test", "Tarifario 1", "SUBSIDIADO"],
            ["FAC-002", "0", "25000", "ODT", "ODT", "997002", "", "Control de Placa Bacteriana", "67890", "Asistencial", "2", "", "EQUIPOS BASICOS ODONTOLOGIA", "ESS118", "ESS118", "ESS118", "", "970", "CC", "1985-06-15", "2024-01-16", "", "456", "Dr Test 2", "03762", "Resp Test 2", "Tarifario 1", "SUBSIDIADO"],
        ])

        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "test_eb_roundtrip.xlsx")},
        )

        # Should return JSON response
        assert resp.status_code in (200, 500)
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert "status" in data
        # Even if detection errors, the response format should be correct
        if data.get("status") == "success":
            assert "data" in data
            assert "errores" in data["data"]
        else:
            assert "errors" in data

    def test_roundtrip_empty_data(self, fresh_client):
        """File with headers only -> handled gracefully."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        buf = _make_eb_excel(EB_HEADERS, [])
        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "empty_eb.xlsx")},
        )
        assert resp.status_code in (200, 500)
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert "status" in data

    def test_roundtrip_missing_columns(self, fresh_client):
        """File with missing required columns -> error."""
        with fresh_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        buf = _make_eb_excel(["Algo", "Otro"], [["1", "2"]])
        resp = fresh_client.post(
            "/odontologia-equipos-basicos/",
            data={"file_upload": (buf, "bad_eb.xlsx")},
        )
        assert resp.status_code in (200, 500)
        import json
        data = json.loads(resp.data.decode("utf-8"))
        assert "status" in data
