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
from app.utils import users_store


def _fake_error() -> dict:
    return {
        "id": "test-i1",
        "estado": "S",
        "tipo_error": "OTROS",
        "observacion": "paciente",
        "observacion_facturador": "",
        "factura": "FAC-001",
        "responsable": "",
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

    # ── Urgencias user (control_urgencias only) ──────────────────────

    def test_put_200_urgencias_allowed_estado(self, app_client):
        """Urgencias user PUT 'estado' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_200_urgencias_allowed_obs_facturador(self, app_client):
        """Urgencias user PUT 'observacion_facturador' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"observacion_facturador": "todo ok"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_403_urgencias_prohibited_field(self, app_client):
        """Urgencias user PUT 'tipo_error' → 403 with field name in body."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "tipo_error" in data["errors"][0]

    def test_put_403_urgencias_mixed_payload(self, app_client):
        """Urgencias user PUT allowed+prohibited → 403, no changes applied."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R", "responsable": "Juan"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "responsable" in data["errors"][0]

    def test_put_403_urgencias_observacion(self, app_client):
        """Urgencias user PUT 'observacion' → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

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
        """User with ce_authenticated but no permisos → 403 for prohibited fields."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            # No permisos key
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


# =============================================================================
# Role-based visibility (sdd control-errores-role-visibility)
# =============================================================================

_FIXTURE_ERRO = [
    {
        "id": "i-lorenya",
        "tipo_error": "Otros",
        "estado": "S",
        "responsable": "LORENY ESPAÑA",
        "creado_en": "2026-08-01T10:00:00",
    },
    {
        "id": "i-unmatched",
        "tipo_error": "Otros",
        "estado": "S",
        "responsable": "UNKNOWN PERSON",
        "creado_en": "2026-08-02T10:00:00",
    },
    {
        "id": "i-daniela",
        "tipo_error": "Otros",
        "estado": "S",
        "responsable": "DANIELA PAEZ",
        "creado_en": "2026-08-03T10:00:00",
    },
]


class TestGetRoleVisibilityIntegration:
    """Spec R1/R2: GET /api/control-errores role matrix via app_client."""

    def _login_session(self, app_client, rol, username, permisos):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = rol
            sess["username"] = username
            sess["permisos"] = permisos

    def test_facturador_own_only(self, app_client):
        """Facturador LORENYA ve solo sus novedades."""
        self._login_session(app_client, "facturador", "LORENYA",
                            ["urgencias", "control_urgencias", "facturas_abiertas"])
        with (
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _FIXTURE_ERRO}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
            patch("app.services.control_errores_service.users_store.get_user",
                  return_value={"primer_nombre": "LORENY ", "apellido_1": "ESPAÑA ",
                                "rol": "facturador"}),
        ):
            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        ids = [e["id"] for e in resp.get_json()["data"]["errores"]]
        assert ids == ["i-lorenya"]
        assert "i-unmatched" not in ids
        assert "i-daniela" not in ids

    def test_validador_sees_all(self, app_client):
        """Validador ve todas las novedades."""
        self._login_session(app_client, "validador", "val1",
                            ["control_urgencias", "control_urgencias:write"])
        with (
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _FIXTURE_ERRO}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
        ):
            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        ids = {e["id"] for e in resp.get_json()["data"]["errores"]}
        assert ids == {"i-lorenya", "i-unmatched", "i-daniela"}

    def test_admin_sees_all(self, app_client):
        """Admin ve todas las novedades."""
        self._login_session(app_client, "admin", "admin", ["*"])
        with (
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _FIXTURE_ERRO}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
        ):
            resp = app_client.get("/api/control-errores")

        assert resp.status_code == 200
        ids = {e["id"] for e in resp.get_json()["data"]["errores"]}
        assert ids == {"i-lorenya", "i-unmatched", "i-daniela"}

    def test_unauthenticated_authorization_error(self, app_client):
        """Sin sesión → 401, no se devuelven datos."""
        resp = app_client.get(
            "/api/control-errores",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["data"] == {}
        assert len(data["errors"]) > 0


class TestAreaFilterIntegration:
    """sdd Empieza: GET /api/control-errores?area=<slug> filtra vía la ruta."""

    def test_get_area_filter_via_route(self, app_client):
        """area=urgencias → solo novedades de responsables de urgencias."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "admin"
            sess["username"] = "admin"
            sess["permisos"] = ["*"]

        facturadores = [
            {"username": "LORENYA", "primer_nombre": "LORENY", "apellido_1": "ESPAÑA",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "LORENY ESPAÑA",
             "rol": "facturador", "areas": ["urgencias"]},
        ]
        with (
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _FIXTURE_ERRO}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=facturadores),
        ):
            resp = app_client.get("/api/control-errores?area=urgencias")

        assert resp.status_code == 200
        ids = [e["id"] for e in resp.get_json()["data"]["errores"]]
        assert ids == ["i-lorenya"]
        assert "i-daniela" not in ids

    def test_get_area_filter_empty_for_other_area(self, app_client):
        """area sin responsables → resultado vacío (contrato aditivo)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "admin"
            sess["username"] = "admin"
            sess["permisos"] = ["*"]

        facturadores = [
            {"username": "LORENYA", "primer_nombre": "LORENY", "apellido_1": "ESPAÑA",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "LORENY ESPAÑA",
             "rol": "facturador", "areas": ["urgencias"]},
        ]
        with (
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _FIXTURE_ERRO}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=facturadores),
        ):
            resp = app_client.get("/api/control-errores?area=ambulatoria")

        assert resp.status_code == 200
        assert resp.get_json()["data"]["errores"] == []


class TestOpcionesAreasIntegration:
    """sdd Empieza: /api/control-errores/opciones expone areas + responsables_detalle."""

    def test_opciones_payload_includes_areas_and_detalle(self, app_client):
        """Payload aditivo: responsables plano + areas (7) + detalle nombre→areas."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "admin"
            sess["username"] = "admin"
            sess["permisos"] = ["*"]

        with patch("app.services.control_errores_service.users_store.get_facturadores",
                   return_value=[
                       {"username": "ANGIEC", "primer_nombre": "ANGIE ", "apellido_1": "ARIAS ",
                        "segundo_nombre": "", "apellido_2": "",
                        "nombre_completo": "ANGIE ARIAS", "rol": "facturador",
                        "areas": ["urgencias", "odontologia"]},
                   ]):
            resp = app_client.get("/api/control-errores/opciones")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        # responsables sigue plano (contrato existente)
        assert data["responsables"] == ["ANGIE ARIAS"]
        # areas: SOLO las 4 canónicas (sin legacy selectable)
        assert [a["slug"] for a in data["areas"]] == [
            "urgencias", "ambulatoria", "extramural", "odontologia",
        ]
        # responsables_detalle: nombre → áreas
        assert data["responsables_detalle"] == [
            {"nombre_completo": "ANGIE ARIAS", "areas": ["urgencias", "odontologia"]}
        ]


class TestAuthAreasIntegration:
    """sdd Empieza: POST /auth/usuarios/* con areas end-to-end vía app_client."""

    def test_post_create_with_areas_end_to_end(self, app_client):
        """POST crear con areas → persistidas y devueltas ordenadas por el store."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.post(
            "/auth/usuarios/crear",
            data={
                "username": "nuevo_user",
                "password": "pass123",
                "rol": "facturador",
                "permisos": ["urgencias"],
                "primer_nombre": "Ana",
                "apellido_1": "López",
                "areas": ["urgencias", "odontologia"],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        user = users_store.get_user("nuevo_user")
        assert user is not None
        assert user["areas"] == ["odontologia", "urgencias"]

    def test_post_edit_with_areas_end_to_end(self, app_client):
        """POST editar con areas → reemplaza el set completo."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        users_store.create_user(
            "nuevo_user", "pass123", "facturador", ["urgencias"],
            areas=["urgencias"],
        )
        resp = app_client.post(
            "/auth/usuarios/nuevo_user/editar",
            data={
                "username": "nuevo_user",
                "rol": "facturador",
                "permisos": ["urgencias"],
                "areas": ["extramural", "odontologia"],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        user = users_store.get_user("nuevo_user")
        assert user["areas"] == ["extramural", "odontologia"]

    def test_post_create_legacy_area_rejected(self, app_client):
        """POST crear con slug legacy → el usuario NO se crea."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.post(
            "/auth/usuarios/crear",
            data={
                "username": "nuevo_user",
                "password": "pass123",
                "rol": "facturador",
                "permisos": ["urgencias"],
                "primer_nombre": "Ana",
                "apellido_1": "López",
                "areas": ["urgencias", "equipos_basicos"],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200  # redirect con flash error
        assert users_store.get_user("nuevo_user") is None

    def test_post_edit_preserves_legacy_persisted_rows(self, app_client):
        """Editar un usuario con filas legacy persistidas NO las borra."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        users_store.create_user(
            "nuevo_user", "pass123", "facturador", ["urgencias"],
            areas=["urgencias"],
        )
        # Semilla histórica: fila legacy ya persistida en user_areas
        db = users_store._new_session()
        try:
            user = db.query(users_store.User).filter_by(username="nuevo_user").one()
            db.add(users_store.UserArea(user_id=user.id, area="derechos"))
            db.commit()
        finally:
            db.close()

        resp = app_client.post(
            "/auth/usuarios/nuevo_user/editar",
            data={
                "username": "nuevo_user",
                "rol": "facturador",
                "permisos": ["urgencias"],
                "areas": ["extramural"],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        user = users_store.get_user("nuevo_user")
        assert user["areas"] == ["derechos", "extramural"]


class TestPostCreatedByIntegration:
    """Spec R5: POST stores created_by from session, ignores client value."""

    def test_post_stores_created_by_from_session(self, app_client):
        """created_by = username de sesión; payload no lo controla."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Maria"
            sess["apellido_1"] = "Gomez"

        with patch("app.services.control_errores_service.crear_error") as mock_crear:
            mock_crear.return_value = {"id": "x", "created_by": "val1", "validador": "Maria Gomez"}
            resp = app_client.post("/api/control-errores", json={
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "LORENY ESPAÑA",
                "observacion": "test",
                "created_by": "hacker",
            })

        assert resp.status_code == 200
        assert mock_crear.call_args.kwargs.get("created_by") == "val1"
        assert resp.get_json()["data"]["error"]["created_by"] == "val1"


class TestOpcionesDbOnlyIntegration:
    """Spec R4: opciones responsables solo desde DB facturadores."""

    def test_opciones_uses_db_facturadores(self, app_client):
        """responsables provienen de get_facturadores; sin key nombres completos."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]

        with patch("app.services.control_errores_service.users_store.get_facturadores",
                   return_value=[
                       {"username": "ANGIEC", "primer_nombre": "ANGIE ", "apellido_1": "ARIAS ",
                        "segundo_nombre": "", "apellido_2": "",
                        "nombre_completo": "ANGIE ARIAS", "rol": "facturador"},
                   ]):
            resp = app_client.get("/api/control-errores/opciones")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["responsables"] == ["ANGIE ARIAS"]
        assert "responsables_nombres_completos" not in data

    def test_opciones_empty_when_no_facturadores(self, app_client):
        """Sin facturadores DB → lista vacía, sin fallback hardcodeado."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]

        with patch("app.services.control_errores_service.users_store.get_facturadores",
                   return_value=[]):
            resp = app_client.get("/api/control-errores/opciones")

        assert resp.status_code == 200
        assert resp.get_json()["data"]["responsables"] == []

    def test_opciones_db_down_returns_error_no_fallback(self, app_client):
        """DB caída → envelope de error; nunca nombres hardcodeados."""
        from sqlalchemy.exc import OperationalError

        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]

        def boom():
            raise OperationalError("SELECT", {}, Exception("connection refused"))

        with patch("app.services.control_errores_service.users_store.get_facturadores",
                   side_effect=boom):
            resp = app_client.get("/api/control-errores/opciones")

        assert resp.status_code == 200  # envelope error, not 500
        data = resp.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0
        # Ningún responsable hardcodeado se filtra en el error
        assert "ALEJANDRA ESPAÑA" not in str(data["errors"])
