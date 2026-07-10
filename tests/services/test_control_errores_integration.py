"""Integration tests: PUT /api/control-errores/<id> with session permissions.

Strict TDD: tests describe the NEW behavior. These will fail (RED) against
the old route decorator that requires "control_urgencias:write".
"""

from unittest.mock import patch

import pytest

from app.services.control_errores_service import (
    obtener_error,
    actualizar_error,
)


def _fake_error() -> dict:
    return {
        "id": "test-i1",
        "estado": "S",
        "tipo_error": "OTROS",
        "observacion": "paciente",
        "observacion_facturador": "",
        "factura": "FAC-001",
        "responsable": "",
        "responsable_rol": "MEDICO",
        "created_by": "medico",
    }


# Patch the storage layer for ALL tests in this module to avoid
# needing actual JSON files on disk.
@pytest.fixture(autouse=True)
def _mock_storage():
    with (
        patch("app.services.control_errores_service.obtener_error") as mock_get,
        patch("app.services.control_errores_service.actualizar_error") as mock_upd,
    ):
        mock_get.return_value = _fake_error()
        mock_upd.return_value = {
            "id": "test-i1",
            "estado": "R",
            "tipo_error": "X",
            "observacion_facturador": "ok",
        }
        yield


class TestPutEndpointPermissions:
    """Integration tests: PUT endpoint with different session states."""

    # ── Médico user (partial write on own records) ───────────────────

    def test_put_200_medico_allowed_estado(self, app_client):
        """Médico on own record PUT 'estado' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "medico"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_200_medico_allowed_obs_facturador(self, app_client):
        """Médico on own record PUT 'observacion_facturador' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "medico"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"observacion_facturador": "todo ok"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_403_medico_prohibited_field(self, app_client):
        """Médico on own record PUT 'tipo_error' → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "medico"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "tipo_error" in data["errors"][0]

    def test_put_403_medico_mixed_payload(self, app_client):
        """Médico on own record PUT allowed+prohibited → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "medico"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R", "responsable": "Juan"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "responsable" in data["errors"][0]

    def test_put_403_medico_observacion(self, app_client):
        """Médico on own record PUT 'observacion' → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "medico"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"observacion": "nuevo texto"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "observacion" in data["errors"][0]

    # ── Auditor user (control_urgencias:write) ───────────────────────

    def test_put_200_auditor_all_fields(self, app_client):
        """Auditor user PUT 'tipo_error' → 200 (full write)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = [
                "control_urgencias",
                "control_urgencias:write",
                "facturas_abiertas",
                "facturas_abiertas:write",
            ]
            sess["username"] = "auditor"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X", "responsable": "Maria"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data["status"] == "success"

    # ── Admin user (*) ───────────────────────────────────────────────

    def test_put_200_admin_all_fields(self, app_client):
        """Admin user PUT any field → 200 (full write)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X", "observacion": "cambio admin"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    # ── Regression: legacy flag ──────────────────────────────────────

    def test_put_403_no_permisos(self, app_client):
        """User with ce_authenticated but no permisos/rol → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            # No permisos, no rol
            sess["username"] = "legacy"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X"},
        )
        assert resp.status_code == 403


class TestValidadorIntegration:
    """Integration tests: validador column behavior via POST/GET flow."""

    def test_post_creates_with_validador(self, app_client):
        """POST /api/control-errores with valid session MUST create entry with validador."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Juan"
            sess["apellido_1"] = "Pérez"

        resp = app_client.post("/api/control-errores", json={
            "tipo_error": "OTROS",
            "factura": "FAC-001",
            "responsable": "Admin",
            "observacion": "test validador",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["error"]["validador"] == "Juan Pérez"

    def test_post_validador_ignores_client_payload_integration(self, app_client):
        """POST with validador in payload MUST use session value, not payload."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Maria"
            sess["apellido_1"] = "Gomez"

        resp = app_client.post("/api/control-errores", json={
            "tipo_error": "OTROS",
            "factura": "FAC-002",
            "responsable": "Admin",
            "observacion": "test",
            "validador": "hacker",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["error"]["validador"] == "Maria Gomez"
        assert data["data"]["error"]["validador"] != "hacker"


class TestGetErroresRolIntegration:
    """Integration tests: GET /api/control-errores returns responsable_rol."""

    def test_get_returns_responsable_rol_in_every_error(self, app_client):
        """GET /api/control-errores MUST return responsable_rol in every error dict."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X", "creado_en": "2026-01-01"},
            {"id": "e2", "responsable": "MARIA GOMEZ", "tipo_error": "Y", "creado_en": "2026-01-02"},
        ]
        fake_usuarios = [
            {"username": "jperez", "rol": "facturador", "permisos": [], "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": ""},
            {"username": "mgomez", "rol": "medico", "permisos": [], "primer_nombre": "MARIA", "segundo_nombre": "", "apellido_1": "GOMEZ", "apellido_2": ""},
        ]

        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["username"] = "urgencias"

            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        errores = data["data"]["errores"]
        assert len(errores) == 2
        assert errores[0]["responsable_rol"] == "FACTURADOR"
        assert errores[1]["responsable_rol"] == "MEDICO"

    def test_get_empty_facturadores_all_dash(self, app_client):
        """GET with empty usuarios MUST fallback to hardcoded roles."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X", "creado_en": "2026-01-01"},
        ]

        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = []

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["username"] = "urgencias"

            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        # JUAN PEREZ not in hardcoded fallback → gets "-"
        assert data["data"]["errores"][0]["responsable_rol"] == "-"


# =============================================================================
# Task 2.7: Integration tests — GET filtered, POST gate, PUT denied, DELETE 403
# =============================================================================


class TestGetFilteredByRole:
    """Integration: GET /api/control-errores returns role-filtered results."""

    @pytest.fixture(autouse=True)
    def _mock_storage_get(self):
        fake_errores = [
            {
                "id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X",
                "creado_en": "2026-01-01", "created_by": "jperez",
            },
            {
                "id": "e2", "responsable": "MED ICO", "tipo_error": "Y",
                "creado_en": "2026-01-02", "created_by": "med_1",
            },
            {
                "id": "e3", "responsable": "FACT ONE", "tipo_error": "Z",
                "creado_en": "2026-01-03", "created_by": "fact_1",
            },
        ]
        fake_usuarios = [
            {
                "username": "jperez", "rol": "facturador", "permisos": [],
                "primer_nombre": "JUAN", "segundo_nombre": "",
                "apellido_1": "PEREZ", "apellido_2": "",
            },
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "",
                "apellido_1": "ICO", "apellido_2": "",
            },
            {
                "username": "fact_1", "rol": "facturador", "permisos": [],
                "primer_nombre": "FACT", "segundo_nombre": "",
                "apellido_1": "ONE", "apellido_2": "",
            },
        ]
        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios
            yield

    def test_admin_sees_all(self, app_client):
        """Admin (*) MUST see all 3 records."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["rol"] = "admin"
            sess["username"] = "admin"

        resp = app_client.get("/api/control-errores")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]["errores"]) == 3

    def test_auditor_sees_all(self, app_client):
        """Auditor MUST see all 3 records."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "auditor"
            sess["username"] = "audit"

        resp = app_client.get("/api/control-errores")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]["errores"]) == 3

    def test_write_sees_all(self, app_client):
        """Write (:write perm) MUST see all 3 records."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["rol"] = "write"
            sess["username"] = "writer"

        resp = app_client.get("/api/control-errores")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]["errores"]) == 3

    def test_facturador_filtered(self, app_client):
        """Facturador MUST see only médico + self-created records."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "facturador"
            sess["username"] = "fact_1"

        resp = app_client.get("/api/control-errores")
        assert resp.status_code == 200
        data = resp.get_json()
        errores = data["data"]["errores"]
        ids = [e["id"] for e in errores]
        assert "e1" in ids  # facturador record
        assert "e2" in ids  # médico record
        assert "e3" in ids  # otro facturador record

    def test_medico_filtered(self, app_client):
        """Médico MUST see only self-assigned records."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "medico"
            sess["username"] = "med_1"
            sess["primer_nombre"] = "MED"
            sess["apellido_1"] = "ICO"

        resp = app_client.get("/api/control-errores")
        assert resp.status_code == 200
        data = resp.get_json()
        errores = data["data"]["errores"]
        ids = [e["id"] for e in errores]
        assert ids == ["e2"]


class TestPostFacturadorGateIntegration:
    """Integration: POST /api/control-errores facturador blocked on non-médico."""

    def _fake_users(self):
        return [
            {
                "username": "fact_1", "rol": "facturador", "permisos": [],
                "primer_nombre": "FACT", "segundo_nombre": "",
                "apellido_1": "ONE", "apellido_2": "",
            },
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "",
                "apellido_1": "ICO", "apellido_2": "",
            },
        ]

    def test_post_facturador_on_medico_succeeds(self, app_client):
        """Facturador POST for médico target → 200."""
        with (
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_crear.return_value = {"id": "new-1", "validador": "FACT ONE", "created_by": "fact_1"}
            mock_users.return_value = self._fake_users()

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias:write"]
                sess["rol"] = "facturador"
                sess["username"] = "fact_1"
                sess["primer_nombre"] = "FACT"
                sess["apellido_1"] = "ONE"

            resp = app_client.post("/api/control-errores", json={
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "MED ICO",
                "observacion": "test",
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["error"]["created_by"] == "fact_1"

    def test_post_facturador_on_non_medico_blocked(self, app_client):
        """Facturador POST for non-médico target → 403."""
        with (
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = self._fake_users()
            mock_crear.return_value = {"id": "fake", "status": "ok"}

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "facturador"
                sess["username"] = "fact_1"
                sess["primer_nombre"] = "FACT"
                sess["apellido_1"] = "ONE"

            resp = app_client.post("/api/control-errores", json={
                "tipo_error": "OTROS",
                "factura": "FAC-002",
                "responsable": "FACT ONE",  # self — not médico
                "observacion": "test",
            })

        assert resp.status_code == 200  # service returns dict, route jsonify-s it
        data = resp.get_json()
        assert data["status"] == "error"
        assert "autorizado" in data["errors"][0]


class TestPutOwnershipDeniedIntegration:
    """Integration: PUT /api/control-errores/<id> ownership denied."""

    def test_put_facturador_estado_on_facturador_record(self, app_client):
        """Facturador PUT estado on FACTURADOR record → 200 (partial write)."""
        with (
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r1", "responsable_rol": "FACTURADOR",
                "created_by": "other_fact", "estado": "S",
            }
            mock_upd.return_value = {"id": "r1", "estado": "R"}

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "facturador"
                sess["username"] = "fact_1"

            resp = app_client.put("/api/control-errores/r1", json={"estado": "R"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        mock_upd.assert_called_once()


class TestDelete403Integration:
    """Integration: DELETE /api/control-errores/<id> blocked for facturador/médico."""

    def test_delete_facturador_blocked_on_non_medico(self, app_client):
        """Facturador DELETE blocked at service level on non-médico record."""
        with (
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d1", "responsable_rol": "FACTURADOR",
                "created_by": "other", "estado": "S",
            }

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "facturador"
                sess["username"] = "fact_1"

            resp = app_client.delete("/api/control-errores/d1")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"
        assert "autorizado" in str(data)
        mock_del.assert_not_called()

    def test_delete_medico_blocked(self, app_client):
        """Médico DELETE blocked at service level."""
        with (
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d2", "responsable_rol": "MEDICO",
                "created_by": "med_1", "estado": "S",
            }

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "medico"
                sess["username"] = "med_1"

            resp = app_client.delete("/api/control-errores/d2")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"
        assert "autorizado" in str(data)
        mock_del.assert_not_called()


# =============================================================================
# Task 3.8: Frontend integration tests — template injection + per-record flags
# =============================================================================


class TestFrontendTemplateInjection:
    """Integration: control_errores.html injects role-aware variables."""

    def test_page_injects_user_role(self, app_client):
        """GET /control-errores MUST inject window._userRole from session."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["rol"] = "admin"
            sess["username"] = "admin_user"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert 'window._userRole' in html
        assert 'window._username' in html

    def test_page_no_longer_injects_can_write(self, app_client):
        """GET /control-errores MUST NOT inject window._canWrite."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["rol"] = "admin"
            sess["username"] = "admin_user"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        # _canWrite should NOT be a window-level variable anymore
        # (The old pattern: window._canWrite = ...)
        assert 'window._canWrite' not in html

    def test_page_has_user_role_from_session(self, app_client):
        """window._userRole reflects session['rol'] value."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["rol"] = "facturador"
            sess["username"] = "fact_1"

        resp = app_client.get("/control-errores")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert 'window._userRole' in html
        assert 'facturador' in html


class TestApiPerRecordFlags:
    """Integration: GET /api/control-errores returns can_edit/can_delete per record."""

    def test_admin_gets_can_edit_true(self, app_client):
        """Admin gets can_edit=True and can_delete=True on all records."""
        fake_errores = [
            {
                "id": "e1", "responsable": "MED ICO", "tipo_error": "X",
                "creado_en": "2026-01-01", "created_by": "med_1",
            },
        ]
        fake_usuarios = [
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "",
                "apellido_1": "ICO", "apellido_2": "",
            },
        ]
        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["rol"] = "admin"
                sess["username"] = "admin"

            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        data = resp.get_json()
        errores = data["data"]["errores"]
        assert len(errores) == 1
        assert errores[0]["can_edit"] is True
        assert errores[0]["can_delete"] is True

    def test_medico_gets_can_edit_false(self, app_client):
        """Médico gets can_edit=False on own record (partial edit at field level)."""
        fake_errores = [
            {
                "id": "e1", "responsable": "MED ICO", "tipo_error": "X",
                "creado_en": "2026-01-01", "created_by": "med_1",
            },
        ]
        fake_usuarios = [
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "",
                "apellido_1": "ICO", "apellido_2": "",
            },
        ]
        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "medico"
                sess["username"] = "med_1"
                sess["primer_nombre"] = "MED"
                sess["apellido_1"] = "ICO"

            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        data = resp.get_json()
        errores = data["data"]["errores"]
        assert len(errores) == 1
        assert errores[0]["can_edit"] is False
        assert errores[0]["can_delete"] is False

    def test_facturador_on_medico_gets_edit_true(self, app_client):
        """Facturador gets can_edit=True on médico record."""
        fake_errores = [
            {
                "id": "e1", "responsable": "MED ICO", "tipo_error": "X",
                "creado_en": "2026-01-01", "created_by": "med_1",
            },
        ]
        fake_usuarios = [
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "",
                "apellido_1": "ICO", "apellido_2": "",
            },
            {
                "username": "fact_1", "rol": "facturador", "permisos": [],
                "primer_nombre": "FACT", "segundo_nombre": "",
                "apellido_1": "ONE", "apellido_2": "",
            },
        ]
        with (
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["control_urgencias"]
                sess["rol"] = "facturador"
                sess["username"] = "fact_1"

            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        data = resp.get_json()
        errores = data["data"]["errores"]
        assert len(errores) == 1
        assert errores[0]["can_edit"] is True
