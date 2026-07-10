"""Tests for control_errores_service: update_error() permission logic.

Strict TDD: tests describe the NEW behavior (field-level permissions via
session["permisos"]) before production changes are made. These tests will
fail (RED) against the old code that uses session["ce_authenticated"].
"""

from unittest.mock import patch

import pytest
from flask import session

from app import create_app
from app.services.control_errores_service import (
    update_error, add_error, get_opciones, get_errores, delete_error,
)
from app.utils.errores_storage import crear_error, actualizar_error

# Application fixture for test request context
_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _fake_error() -> dict:
    return {
        "id": "test-1",
        "estado": "S",
        "tipo_error": "OTROS",
        "observacion": "paciente",
        "observacion_facturador": "",
        "factura": "FAC-001",
        "responsable": "",
    }


class TestUpdateErrorPermissions:
    """Unit tests for field-level write permissions in update_error()."""

    # ── Full write permission scenarios ──────────────────────────────

    def test_admin_star_can_update_any_field(self):
        """User with '*' (admin) MUST be able to update any field."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["*"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "Juan"}

            result = update_error("test-1", {"responsable": "Juan", "tipo_error": "X"})

        assert result["status"] == "success"
        assert result["data"]["error"]["id"] == "test-1"
        mock_upd.assert_called_once()

    def test_write_perm_can_update_any_field(self):
        """User with 'control_urgencias:write' MUST be able to update any field."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["urgencias", "control_urgencias:write"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "Maria"}

            result = update_error("test-1", {"responsable": "Maria"})

        assert result["status"] == "success"
        assert result["data"]["error"]["id"] == "test-1"
        mock_upd.assert_called_once()

    # ── Partial write (control_urgencias) — now via médico on own record ─

    def test_limited_allowed_estado(self):
        """Médico on own record MUST be allowed to update 'estado' (partial write)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["rol"] = "medico"
            session["ce_authenticated"] = True
            mock_get.return_value = {
                "id": "test-1", "estado": "S", "responsable_rol": "MEDICO",
                "created_by": "", "tipo_error": "OTROS",
            }
            mock_upd.return_value = {"id": "test-1", "estado": "R"}

            result = update_error("test-1", {"estado": "R"})

        assert result["status"] == "success"
        assert result["data"]["error"]["estado"] == "R"
        mock_upd.assert_called_once()

    def test_limited_allowed_observacion_facturador(self):
        """Médico on own record MUST be allowed to update 'observacion_facturador'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["rol"] = "medico"
            session["ce_authenticated"] = True
            mock_get.return_value = {
                "id": "test-1", "estado": "S", "responsable_rol": "MEDICO",
                "created_by": "", "tipo_error": "OTROS",
            }
            mock_upd.return_value = {"id": "test-1", "observacion_facturador": "Ok"}

            result = update_error("test-1", {"observacion_facturador": "Ok"})

        assert result["status"] == "success"
        assert result["data"]["error"]["observacion_facturador"] == "Ok"
        mock_upd.assert_called_once()

    # ── Partial write — prohibited fields on médico ──────────────────

    def test_limited_rejects_prohibited_field(self):
        """Médico on own record MUST get 403 for 'tipo_error' (full-edit field)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["rol"] = "medico"
            session["ce_authenticated"] = True
            mock_get.return_value = {
                "id": "test-1", "estado": "S", "responsable_rol": "MEDICO",
                "created_by": "", "tipo_error": "OTROS",
            }

            result = update_error("test-1", {"tipo_error": "X"})

        # Expect a tuple (dict, 403)
        assert isinstance(result, tuple)
        assert result[1] == 403
        assert result[0]["status"] == "error"
        assert "tipo_error" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_mixed_payload(self):
        """Médico on own MUST reject payload with mixed allowed+prohibited."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["rol"] = "medico"
            session["ce_authenticated"] = True
            mock_get.return_value = {
                "id": "test-1", "estado": "S", "responsable_rol": "MEDICO",
                "created_by": "", "tipo_error": "OTROS",
            }

            result = update_error("test-1", {"estado": "R", "responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "responsable" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_observacion(self):
        """Médico on own MUST NOT edit 'observacion' directly (only estado/obs_facturador)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["rol"] = "medico"
            session["ce_authenticated"] = True
            mock_get.return_value = {
                "id": "test-1", "estado": "S", "responsable_rol": "MEDICO",
                "created_by": "", "tipo_error": "OTROS",
            }

            result = update_error("test-1", {"observacion": "nuevo texto"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "observacion" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    # ── Regression: legacy flag should not affect outcome ────────────

    def test_legacy_flag_ignored_when_has_write_perm(self):
        """ce_authenticated=False MUST NOT block when permisos has :write."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["ce_authenticated"] = False
            session["permisos"] = ["control_urgencias:write"]
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "tipo_error": "X"}

            result = update_error("test-1", {"tipo_error": "X"})

        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_no_permisos_restricts_fields(self):
        """No permisos/rol in session MUST 403 via ownership gate."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["ce_authenticated"] = True
            # No session["permisos"] or session["rol"] set
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "autorizado" in result[0]["errors"][0]
        mock_upd.assert_not_called()


class TestValidadorColumn:
    """Tests: validador column — storage, service composition, and backward compat.
    
    Strict TDD: tests written BEFORE production changes. These will fail (RED)
    until storage and service code is updated.
    """

    # ── Storage: crear_error ──────────────────────────────────────────

    def test_crear_error_stores_validador_key(self):
        """crear_error() MUST store validador key when validador param is passed."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-001",
                observacion="test obs",
                estado="S",
                responsable="Admin",
                validador="Juan Pérez",
            )

        assert error["validador"] == "Juan Pérez"
        mock_write.assert_called_once()

    def test_crear_error_validador_default_empty(self):
        """crear_error() MUST default validador to empty string."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-002",
                observacion="no validador",
                estado="S",
                responsable="Admin",
            )

        assert error["validador"] == ""
        mock_write.assert_called_once()

    # ── Service: add_error composition ────────────────────────────────

    def test_add_error_composes_validador_from_session(self):
        """add_error() MUST compose validador from session['primer_nombre'] + session['apellido_1']."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            session["primer_nombre"] = "Juan"
            session["apellido_1"] = "Pérez"
            session["permisos"] = ["*"]
            session["rol"] = "admin"
            mock_users.return_value = []

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "Admin",
                "observacion": "test",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == "Juan Pérez"

    def test_add_error_validador_ignores_client_payload(self):
        """add_error() MUST NOT use validador from client payload — session always wins."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            session["primer_nombre"] = "Maria"
            session["apellido_1"] = "Gomez"
            session["permisos"] = ["*"]
            session["rol"] = "admin"
            mock_users.return_value = []

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "Admin",
                "validador": "hacker",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == "Maria Gomez"

    def test_add_error_validador_session_keys_missing(self):
        """add_error() MUST handle missing session keys gracefully (empty string fallback)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            # No session keys set — should fall back to empty
            session["permisos"] = ["*"]
            session["rol"] = "admin"
            mock_users.return_value = []
            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-003",
                "responsable": "Admin",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == ""

    # ── Storage: actualizar_error does NOT touch validador ─────────────

    def test_actualizar_error_does_not_accept_validador(self):
        """actualizar_error() MUST NOT accept a validador parameter."""
        with patch("app.utils.errores_storage._leer_datos") as mock_read, \
             patch("app.utils.errores_storage._escribir_datos") as mock_write:

            mock_read.return_value = {"errores": [{"id": "test-1", "validador": "old"}]}

            result = actualizar_error(
                error_id="test-1",
                estado="N",
            )

            assert result is not None
            # validador should remain unchanged
            assert result.get("validador") == "old"
            # Verify TypeError if validador is passed
            import inspect
            sig = inspect.signature(actualizar_error)
            assert "validador" not in sig.parameters


# =============================================================================
# Tests: get_opciones() — dynamic responsables from facturadores
# =============================================================================


class TestGetOpcionesFacturadores:
    """Spec R3/R4: get_opciones() pulls from get_facturadores(), fallback to hardcode."""

    def test_dynamic_from_facturadores(self):
        """Facturadores exist → responsables come from get_facturadores()."""
        from app.constants import ERROR_TIPO_URGENCIAS, ERROR_ESTADO_URGENCIAS

        fake_usuarios = [
            {
                "username": "jperez",
                "rol": "facturador",
                "permisos": [],
                "primer_nombre": "JUAN",
                "segundo_nombre": "",
                "apellido_1": "PEREZ",
                "apellido_2": "",
            },
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_usuarios
            result = get_opciones()

        assert isinstance(result, dict)
        assert result["responsables"] == ["JUAN PEREZ"]
        assert result["responsables_nombres_completos"] == {
            "JUAN PEREZ": "JUAN PEREZ",
        }
        assert result["tipos_error"] == ERROR_TIPO_URGENCIAS
        assert result["estados"] == ERROR_ESTADO_URGENCIAS

    def test_nombres_completos_incluye_todos_los_campos(self):
        """responsables_nombres_completos includes all 4 name parts joined."""
        fake_usuarios = [
            {
                "username": "jperez",
                "rol": "facturador",
                "permisos": [],
                "primer_nombre": "JUAN",
                "segundo_nombre": "FELIPE",
                "apellido_1": "PEREZ",
                "apellido_2": "GOMEZ",
            },
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_usuarios
            result = get_opciones()

        assert result["responsables_nombres_completos"] == {
            "JUAN PEREZ": "JUAN FELIPE PEREZ GOMEZ",
        }

    def test_fallback_when_empty(self):
        """No usuarios → fallback to hardcoded constants."""
        from app.constants import (
            ERROR_RESPONSABLE_URGENCIAS,
            RESPONSABLE_NOMBRES_COMPLETOS,
        )

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = []
            result = get_opciones()

        assert isinstance(result, dict)
        assert result["responsables"] == ERROR_RESPONSABLE_URGENCIAS
        assert result["responsables_nombres_completos"] == RESPONSABLE_NOMBRES_COMPLETOS

    def test_same_response_shape_preserved(self):
        """Response keys remain identical regardless of source."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = [
                {
                    "username": "test",
                    "rol": "facturador",
                    "permisos": [],
                    "primer_nombre": "A",
                    "segundo_nombre": "",
                    "apellido_1": "B",
                    "apellido_2": "",
                },
            ]
            result = get_opciones()

        assert "tipos_error" in result
        assert "estados" in result
        assert "responsables" in result
        assert "responsables_nombres_completos" in result
        assert "responsables_roles" in result

    def test_nombre_completo_uppercase(self):
        """Name format: primer_nombre + apellido_1 uppercase."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = [
                {
                    "username": "ana",
                    "rol": "facturador",
                    "permisos": [],
                    "primer_nombre": "Ana",
                    "segundo_nombre": "",
                    "apellido_1": "López",
                    "apellido_2": "",
                },
            ]
            result = get_opciones()

        assert "ANA LÓPEZ" in result["responsables"]
        assert "Ana López" not in result["responsables"]

    def test_transition_from_fallback_to_dynamic(self):
        """R4: create first facturador → next get_opciones() returns dynamic, not fallback."""
        from app.constants import ERROR_RESPONSABLE_URGENCIAS

        facturador_payload = [
            {
                "username": "nuevo_fact",
                "rol": "facturador",
                "permisos": [],
                "primer_nombre": "NUEVO",
                "segundo_nombre": "",
                "apellido_1": "FACTURADOR",
                "apellido_2": "",
            },
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            # Phase 1: no usuarios → fallback
            mock_users.return_value = []
            result_empty = get_opciones()
            assert result_empty["responsables"] == ERROR_RESPONSABLE_URGENCIAS
            assert result_empty["responsables_nombres_completos"] != {}

            # Phase 2: after creating first user → dynamic
            mock_users.return_value = facturador_payload
            result_dynamic = get_opciones()
            assert result_dynamic["responsables"] == ["NUEVO FACTURADOR"]
            assert result_dynamic["responsables_nombres_completos"] == {
                "NUEVO FACTURADOR": "NUEVO FACTURADOR",
            }


# =============================================================================
# Tests: get_errores() — rol enrichment from list_users()
# =============================================================================


class TestGetErroresRolEnrichment:
    """Spec R12: get_errores() MUST inject responsable_rol from list_users()."""

    # ── Happy path ────────────────────────────────────────────────────

    def test_rol_mapped_from_facturadores(self):
        """get_errores() MUST map responsable → rol using list_users()."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X"},
            {"id": "e2", "responsable": "MARIA GOMEZ", "tipo_error": "Y"},
        ]
        fake_usuarios = [
            {"username": "jperez", "rol": "facturador", "permisos": [], "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": ""},
            {"username": "mgomez", "rol": "medico", "permisos": [], "primer_nombre": "MARIA", "segundo_nombre": "", "apellido_1": "GOMEZ", "apellido_2": ""},
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            result = get_errores()

        assert result["status"] == "success"
        errores = result["data"]["errores"]
        assert errores[0]["responsable_rol"] == "FACTURADOR"
        assert errores[1]["responsable_rol"] == "MEDICO"

    def test_rol_unmatched_responsable_fallsback_to_dash(self):
        """Unmatched responsable name MUST result in '-'."""
        fake_errores = [
            {"id": "e1", "responsable": "NOBODY", "tipo_error": "X"},
        ]
        fake_usuarios = [
            {"username": "jperez", "rol": "facturador", "permisos": [], "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": ""},
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            result = get_errores()

        errores = result["data"]["errores"]
        assert errores[0]["responsable_rol"] == "-"

    # ── Edge cases (task 1.2) ─────────────────────────────────────────

    def test_empty_facturadores_all_dash(self):
        """Empty usuarios list MUST fallback to hardcoded roles."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X"},
            {"id": "e2", "responsable": "MARIA GOMEZ", "tipo_error": "Y"},
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = []

            result = get_errores()

        errores = result["data"]["errores"]
        # When no users, the fallback hardcoded roles are used (not "-")
        # So JUAN PEREZ is not in the hardcoded fallback → gets "-"
        assert all(e["responsable_rol"] == "-" for e in errores) is True

    def test_facturador_missing_rol_key_fallsback_to_dash(self):
        """User dict without 'rol' key MUST use .get('rol', '-') → '-'."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X"},
        ]
        fake_usuarios = [
            {"username": "jperez", "permisos": [], "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": ""},
            # No "rol" key
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            result = get_errores()

        errores = result["data"]["errores"]
        assert errores[0]["responsable_rol"] == "-"


# =============================================================================
# Tasks 1.1 + 1.2: created_by field + auditor role (PR 1 Foundation)
# =============================================================================


class TestCrearErrorCreatedBy:
    """Task 1.1: crear_error() MUST accept and store created_by param."""

    def test_crear_error_stores_created_by(self):
        """crear_error() MUST store created_by key when param is passed."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-001",
                observacion="test obs",
                estado="S",
                responsable="Admin",
                validador="Juan Pérez",
                created_by="jperez",
            )

        assert error["created_by"] == "jperez"
        mock_write.assert_called_once()

    def test_crear_error_created_by_default_empty(self):
        """crear_error() MUST default created_by to empty string."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-002",
                observacion="no created_by",
                estado="S",
                responsable="Admin",
            )

        assert error["created_by"] == ""
        mock_write.assert_called_once()

    def test_crear_error_stores_both_validador_and_created_by(self):
        """crear_error() MUST store both validador (display name) and created_by (username)."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-003",
                observacion="dual fields",
                estado="S",
                responsable="Admin",
                validador="Juan Pérez",
                created_by="jperez",
            )

        assert error["validador"] == "Juan Pérez"
        assert error["created_by"] == "jperez"
        mock_write.assert_called_once()


class TestUpdateUserAuditor:
    """Task 1.2: update_user() MUST accept 'auditor' as valid role."""

    def test_auditor_role_is_allowed(self):
        """update_user() MUST accept 'auditor' as valid rol without error."""
        fake_users = [
            {
                "username": "audit_user",
                "password_hash": "hash",
                "rol": "usuario",
                "permisos": [],
                "primer_nombre": "",
                "segundo_nombre": "",
                "apellido_1": "",
                "apellido_2": "",
            },
        ]

        with patch("app.utils.users_store._load_users") as mock_load, \
             patch("app.utils.users_store._save_users") as mock_save:
            mock_load.return_value = fake_users

            from app.utils.users_store import update_user
            result = update_user("audit_user", {"rol": "auditor"})

        assert result[0] is True
        assert "actualizado" in result[1]
        mock_save.assert_called_once()

    def test_auditor_role_is_allowed_lowercase(self):
        """update_user() MUST reject 'AUDITOR' — case-sensitive validation."""
        fake_users = [
            {
                "username": "audit_user",
                "password_hash": "hash",
                "rol": "usuario",
                "permisos": [],
                "primer_nombre": "",
                "segundo_nombre": "",
                "apellido_1": "",
                "apellido_2": "",
            },
        ]

        with patch("app.utils.users_store._load_users") as mock_load, \
             patch("app.utils.users_store._save_users") as mock_save:
            mock_load.return_value = fake_users

            from app.utils.users_store import update_user
            result = update_user("audit_user", {"rol": "AUDITOR"})

        assert result[0] is False
        assert "Rol inválido" in result[1]
        mock_save.assert_not_called()

    def test_auditor_role_persisted_correctly(self):
        """The auditor role MUST be stored exactly as provided to update_user()."""
        fake_users = [
            {
                "username": "audit_user",
                "password_hash": "hash",
                "rol": "usuario",
                "permisos": [],
                "primer_nombre": "",
                "segundo_nombre": "",
                "apellido_1": "",
                "apellido_2": "",
            },
        ]

        with patch("app.utils.users_store._load_users") as mock_load, \
             patch("app.utils.users_store._save_users") as mock_save:
            mock_load.return_value = fake_users

            from app.utils.users_store import update_user
            update_user("audit_user", {"rol": "auditor"})

        # Verify the saved users list has "auditor" as the rol
        saved_users = mock_save.call_args[0][0]
        assert saved_users[0]["rol"] == "auditor"


# =============================================================================
# Tasks 1.3-1.10: Permission helpers (PR 1 Foundation)
# =============================================================================


class TestResolveEffectiveRole:
    """Task 1.3+1.4: _resolve_effective_role() resolves role from permisos + rol."""

    # ── Admin ("*" in permisos) ──────────────────────────────────────

    def test_star_permiso_becomes_admin(self):
        """'*' in permisos MUST resolve to 'admin' regardless of session rol."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(["*"], "usuario") == "admin"
        assert _resolve_effective_role(["*"], "facturador") == "admin"
        assert _resolve_effective_role(["*"], "admin") == "admin"

    def test_star_permiso_beats_other_permisos(self):
        """'*' with other permisos STILL resolves to 'admin'."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(
            ["*", "control_urgencias:write"], "usuario"
        ) == "admin"

    # ── Write (":write" in permisos) ──────────────────────────────────

    def test_write_permiso_resolves_to_write(self):
        """Any ':write' permiso MUST resolve to 'write' (no '*')."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(
            ["control_urgencias:write"], "usuario"
        ) == "write"
        assert _resolve_effective_role(
            ["facturas_abiertas:write"], "facturador"
        ) == "write"

    def test_write_permiso_does_not_beat_star(self):
        """If '*' is present, it MUST resolve to 'admin', not 'write'."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(
            ["*", "control_urgencias:write"], "usuario"
        ) == "admin"

    # ── Fallback to session["rol"] ────────────────────────────────────

    def test_no_special_permiso_fallsback_to_rol(self):
        """No '*' and no ':write' MUST fall back to session rol."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(
            ["control_urgencias"], "facturador"
        ) == "facturador"
        assert _resolve_effective_role(
            ["urgencias"], "medico"
        ) == "medico"
        assert _resolve_effective_role(
            [], "auditor"
        ) == "auditor"

    def test_rol_none_fallsback_to_read(self):
        """rol is None or missing MUST default to 'read'."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(None, None) == "read"
        assert _resolve_effective_role([], "") == "read"

    def test_empty_permisos_medico_rol(self):
        """Empty permisos + 'medico' rol → 'medico' (preserved)."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role([], "medico") == "medico"

    def test_auditor_rol_with_write_permiso(self):
        """Auditor rol with ':write' permiso → 'write'."""
        from app.services.control_errores_service import _resolve_effective_role

        assert _resolve_effective_role(
            ["control_urgencias:write"], "auditor"
        ) == "write"


class TestCanEdit:
    """Task 1.5+1.6: _can_edit() per-role + per-record ownership check."""

    # ── Admin / Auditor / Write — always True ─────────────────────────

    def test_admin_always_can_edit(self):
        """admin, auditor, write MUST always return True."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r1", "responsable_rol": "FACTURADOR", "created_by": "other"}
        assert _can_edit(record, "admin", "admin_user") is True
        assert _can_edit(record, "auditor", "auditor_user") is True
        assert _can_edit(record, "write", "write_user") is True

    def test_write_can_edit_any_record(self):
        """write user can edit any record regardless of ownership."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r2", "responsable_rol": "FACTURADOR", "created_by": "someone_else"}
        assert _can_edit(record, "write", "current_user") is True

    # ── Facturador — only médico records ──────────────────────────────

    def test_facturador_can_edit_medico_record(self):
        """facturador MUST be allowed on records with responsable_rol == 'MEDICO'."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r3", "responsable_rol": "MEDICO", "created_by": "dr_medico"}
        assert _can_edit(record, "facturador", "fact_user") is True

    def test_facturador_can_edit_own_created_record(self):
        """facturador MUST be allowed on records they created (created_by == username)."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r4", "responsable_rol": "FACTURADOR", "created_by": "fact_user"}
        assert _can_edit(record, "facturador", "fact_user") is True

    def test_facturador_blocked_on_non_medico_non_own(self):
        """facturador MUST be blocked on non-médico records not created by them."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r5", "responsable_rol": "FACTURADOR", "created_by": "other_fact"}
        assert _can_edit(record, "facturador", "fact_user") is False

    # ── Médico — only self-assigned records ───────────────────────────

    def test_medico_can_edit_own_record(self):
        """médico MUST be allowed on records where created_by == their username."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r6", "responsable_rol": "MEDICO", "created_by": "dr_medico"}
        assert _can_edit(record, "medico", "dr_medico") is True

    def test_medico_blocked_on_other_medico_record(self):
        """médico MUST be blocked on records created by another médico."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r7", "responsable_rol": "MEDICO", "created_by": "other_medico"}
        assert _can_edit(record, "medico", "dr_medico") is False

    def test_medico_blocked_on_facturador_record(self):
        """médico MUST be blocked on records not assigned to them."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r8", "responsable_rol": "FACTURADOR", "created_by": "fact_user"}
        assert _can_edit(record, "medico", "dr_medico") is False

    # ── Read — never can edit ─────────────────────────────────────────

    def test_read_role_cannot_edit(self):
        """read role MUST return False for any record."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r9", "responsable_rol": "MEDICO", "created_by": "anyone"}
        assert _can_edit(record, "read", "reader") is False

    # ── Legacy records (created_by is None) ───────────────────────────

    def test_legacy_record_admin_can_edit(self):
        """Legacy record (created_by=None) MUST be editable by admin/auditor/write."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r10", "responsable_rol": "FACTURADOR"}
        assert _can_edit(record, "admin", "admin") is True
        assert _can_edit(record, "auditor", "audit") is True
        assert _can_edit(record, "write", "writer") is True

    def test_legacy_record_facturador_blocked(self):
        """Legacy record (created_by=None) MUST be blocked for facturador
        when responsable_rol is not MEDICO."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r11", "responsable_rol": "FACTURADOR"}
        assert _can_edit(record, "facturador", "fact_user") is False

    def test_legacy_record_medico_blocked(self):
        """Legacy record (created_by=None) MUST be blocked for médico."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r12", "responsable_rol": "MEDICO"}
        assert _can_edit(record, "medico", "dr_medico") is False

    def test_legacy_record_facturador_allowed_on_medico(self):
        """Legacy médico record (created_by=None, responsable_rol=MEDICO) MUST be
        editable by facturador via responsable_rol path."""
        from app.services.control_errores_service import _can_edit

        record = {"id": "r13", "responsable_rol": "MEDICO"}
        assert _can_edit(record, "facturador", "fact_user") is True


class TestCanDelete:
    """Task 1.7+1.8: _can_delete() per-role delete permission check."""

    # ── Admin / Auditor / Write — always True ─────────────────────────

    def test_admin_auditor_write_can_delete(self):
        """admin, auditor, write MUST always return True for delete."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d1", "responsable_rol": "FACTURADOR", "created_by": "other"}
        assert _can_delete(record, "admin") is True
        assert _can_delete(record, "auditor") is True
        assert _can_delete(record, "write") is True

    # ── Facturador — only médico records ──────────────────────────────

    def test_facturador_can_delete_medico_record(self):
        """facturador MUST be allowed to delete records with responsable_rol == 'MEDICO'."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d2", "responsable_rol": "MEDICO", "created_by": "dr_medico"}
        assert _can_delete(record, "facturador") is True

    def test_facturador_blocked_on_non_medico(self):
        """facturador MUST be blocked on non-médico records."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d3", "responsable_rol": "FACTURADOR", "created_by": "other_fact"}
        assert _can_delete(record, "facturador") is False

    def test_facturador_blocked_on_own_record_if_not_medico(self):
        """facturador's own record is NOT deletable unless responsable_rol is MEDICO."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d4", "responsable_rol": "FACTURADOR", "created_by": "fact_user"}
        assert _can_delete(record, "facturador") is False

    # ── Médico — never True ───────────────────────────────────────────

    def test_medico_cannot_delete(self):
        """médico MUST always return False for delete."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d5", "responsable_rol": "MEDICO", "created_by": "dr_medico"}
        assert _can_delete(record, "medico") is False

    # ── Read / unknown — always False ─────────────────────────────────

    def test_read_cannot_delete(self):
        """read role MUST always return False for delete."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d6", "responsable_rol": "MEDICO", "created_by": "anyone"}
        assert _can_delete(record, "read") is False

    # ── Legacy records ────────────────────────────────────────────────

    def test_legacy_record_facturador_allowed_on_medico(self):
        """Legacy médico record (created_by=None) MUST be deletable by facturador."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d7", "responsable_rol": "MEDICO"}
        assert _can_delete(record, "facturador") is True

    def test_legacy_record_facturador_blocked_on_non_medico(self):
        """Legacy non-médico record MUST NOT be deletable by facturador."""
        from app.services.control_errores_service import _can_delete

        record = {"id": "d8", "responsable_rol": "FACTURADOR"}
        assert _can_delete(record, "facturador") is False


class TestCanCreateFor:
    """Task 1.9+1.10: _can_create_for() per-role create permission check."""

    # ── Facturador — only médico target ───────────────────────────────

    def test_facturador_can_create_for_medico(self):
        """facturador MUST be allowed to create for target_rol='medico'."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "facturador") is True
        assert _can_create_for("MEDICO", "facturador") is True

    def test_facturador_blocked_for_non_medico(self):
        """facturador MUST be blocked creating for non-médico targets."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("facturador", "facturador") is False
        assert _can_create_for("admin", "facturador") is False
        assert _can_create_for("usuario", "facturador") is False

    # ── Admin / Auditor / Write — any target ──────────────────────────

    def test_admin_can_create_for_any(self):
        """admin, auditor, write MUST be allowed to create for any target."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "admin") is True
        assert _can_create_for("facturador", "admin") is True
        assert _can_create_for("admin", "admin") is True

    def test_auditor_can_create_for_any(self):
        """auditor MUST be allowed to create for any target_rol."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "auditor") is True
        assert _can_create_for("facturador", "auditor") is True

    def test_write_can_create_for_any(self):
        """write MUST be allowed to create for any target_rol."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "write") is True
        assert _can_create_for("facturador", "write") is True

    # ── Médico — never True ───────────────────────────────────────────

    def test_medico_cannot_create(self):
        """médico MUST be blocked from creating for any target."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "medico") is False
        assert _can_create_for("facturador", "medico") is False

    # ── Read / unknown — always False ─────────────────────────────────

    def test_read_cannot_create(self):
        """read role MUST be blocked from creating."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "read") is False

    def test_unknown_role_cannot_create(self):
        """Unknown roles MUST default to blocked."""
        from app.services.control_errores_service import _can_create_for

        assert _can_create_for("medico", "unknown") is False


# =============================================================================
# Tasks 2.1+2.2+2.3: add_error created_by + facturador gate + session param
# =============================================================================


class TestAddErrorCreatedByFromSession:
    """Task 2.1: add_error() sets created_by from session dict param (PM2)."""

    def test_created_by_from_session_dict(self):
        """add_error(data, session) MUST set created_by from session['username']."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            session_dict = {
                "username": "jperez",
                "primer_nombre": "Juan",
                "apellido_1": "Perez",
                "permisos": ["*"],
                "rol": "admin",
            }

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "Admin",
                "observacion": "test",
            }, session=session_dict)

            mock_crear.assert_called_once()
            call_kwargs = mock_crear.call_args.kwargs
            assert call_kwargs.get("created_by") == "jperez"

    def test_client_created_by_stripped(self):
        """PM2: client payload 'created_by' MUST be ignored — server-side only."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            session_dict = {
                "username": "admin_user",
                "primer_nombre": "Admin",
                "apellido_1": "System",
                "permisos": ["*"],
                "rol": "admin",
            }

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-002",
                "responsable": "Admin",
                "observacion": "test",
                "created_by": "hacker",
            }, session=session_dict)

            mock_crear.assert_called_once()
            call_kwargs = mock_crear.call_args.kwargs
            assert call_kwargs.get("created_by") == "admin_user"

    def test_created_by_backward_compat_no_session_param(self):
        """Without session param, MUST fallback to flask.session for created_by."""
        with _APP.test_request_context():
            session["username"] = "legacy_user"
            session["primer_nombre"] = "Old"
            session["apellido_1"] = "Code"
            session["permisos"] = ["*"]
            session["rol"] = "admin"

            with patch("app.services.control_errores_service.crear_error") as mock_crear:
                add_error({
                    "tipo_error": "OTROS",
                    "factura": "FAC-003",
                    "responsable": "Admin",
                })

            call_kwargs = mock_crear.call_args.kwargs
            assert call_kwargs.get("created_by") == "legacy_user"


class TestAddErrorFacturadorGate:
    """Task 2.2: facturador create gate — only médico targets per PM4/R14."""

    def _mock_users_facturador_and_medico(self):
        """Return fake users: 1 facturador, 1 medico."""
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

    def test_facturador_403_on_non_medico_target(self):
        """PM4: facturador creating for non-médico target → error 403."""
        fake_users = self._mock_users_facturador_and_medico()

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_users
            session_dict = {
                "username": "fact_1",
                "primer_nombre": "FACT",
                "apellido_1": "ONE",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "FACT ONE",  # This is a facturador, not médico
                "observacion": "test",
            }, session=session_dict)

        assert result["status"] == "error"
        mock_crear.assert_not_called()

    def test_facturador_200_on_medico_target(self):
        """PM4: facturador creating for médico target → success."""
        fake_users = self._mock_users_facturador_and_medico()

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_users
            session_dict = {
                "username": "fact_1",
                "primer_nombre": "FACT",
                "apellido_1": "ONE",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-002",
                "responsable": "MED ICO",  # This is a médico
                "observacion": "test",
            }, session=session_dict)

        assert result["status"] == "success"
        mock_crear.assert_called_once()
        call_kwargs = mock_crear.call_args.kwargs
        assert call_kwargs.get("created_by") == "fact_1"

    def test_admin_can_create_for_any_target(self):
        """Admin can create for any target role without restriction."""
        fake_users = self._mock_users_facturador_and_medico()

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_users
            session_dict = {
                "username": "admin_1",
                "primer_nombre": "Admin",
                "apellido_1": "User",
                "permisos": ["*"],
                "rol": "admin",
            }

            result = add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-003",
                "responsable": "FACT ONE",  # facturador target
                "observacion": "test",
            }, session=session_dict)

        assert result["status"] == "success"
        mock_crear.assert_called_once()

    def test_medico_cannot_create_any_record(self):
        """R15: médico role MUST be blocked from creating records (server-side)."""
        fake_users = self._mock_users_facturador_and_medico()

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_users.return_value = fake_users
            session_dict = {
                "username": "med_1",
                "primer_nombre": "MED",
                "apellido_1": "ICO",
                "permisos": ["control_urgencias"],
                "rol": "medico",
            }

            result = add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-004",
                "responsable": "MED ICO",  # self target
                "observacion": "test",
            }, session=session_dict)

        assert result["status"] == "error"
        mock_crear.assert_not_called()


class TestUpdateErrorSessionParam:
    """Task 2.3: update_error() accepts session dict param."""

    def test_update_error_accepts_session_param(self):
        """update_error() MUST accept and use a session dict param."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "estado": "R"}

            session_dict = {
                "username": "admin_1",
                "permisos": ["*"],
                "rol": "admin",
            }

            result = update_error("test-1", {"estado": "R"}, session=session_dict)

        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_update_error_backward_compat_no_session(self):
        """update_error() without session param MUST fallback to flask.session."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["*"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "Juan"}

            result = update_error("test-1", {"responsable": "Juan"})

        assert result["status"] == "success"
        mock_upd.assert_called_once()


class TestDeleteErrorSessionParam:
    """Task 2.3: delete_error() accepts session dict param."""

    def test_delete_error_accepts_session_param(self):
        """delete_error() MUST accept and use a session dict param."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = _fake_error()
            mock_del.return_value = True

            session_dict = {
                "username": "admin_1",
                "permisos": ["*"],
                "rol": "admin",
            }

            result = delete_error("test-1", session=session_dict)

        assert result["status"] == "success"
        mock_del.assert_called_with("test-1")

    def test_delete_error_backward_compat_no_session(self):
        """delete_error() without session param MUST fallback to flask.session."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = _fake_error()
            mock_del.return_value = True
            session["permisos"] = ["*"]

            result = delete_error("test-1")

        assert result["status"] == "success"


class TestGetErroresSessionParam:
    """Task 2.3: get_errores() accepts session dict param."""

    def test_get_errores_accepts_session_param(self):
        """get_errores() MUST accept a session dict keyword param."""
        fake_errores = [
            {"id": "e1", "responsable": "JUAN PEREZ", "tipo_error": "X", "creado_en": "2026-01-01"},
        ]
        fake_usuarios = [
            {"username": "jperez", "rol": "facturador", "permisos": [],
             "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": ""},
        ]

        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = fake_errores
            mock_users.return_value = fake_usuarios

            session_dict = {
                "username": "jperez",
                "permisos": ["*"],
                "rol": "admin",
            }

            result = get_errores(session=session_dict)

        assert result["status"] == "success"
        assert len(result["data"]["errores"]) == 1


# =============================================================================
# Task 2.4: get_errores() — role-based filtering + per-record flags (PM1, PM6)
# =============================================================================


class TestGetErroresRoleFilter:
    """Task 2.4: get_errores() filters records by effective role (R13/PM1)."""

    @staticmethod
    def _fake_records():
        return [
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

    @staticmethod
    def _fake_users():
        return [
            {
                "username": "jperez", "rol": "facturador", "permisos": [],
                "primer_nombre": "JUAN", "segundo_nombre": "", "apellido_1": "PEREZ", "apellido_2": "",
            },
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "", "apellido_1": "ICO", "apellido_2": "",
            },
            {
                "username": "fact_1", "rol": "facturador", "permisos": [],
                "primer_nombre": "FACT", "segundo_nombre": "", "apellido_1": "ONE", "apellido_2": "",
            },
        ]

    def test_admin_sees_all_records(self):
        """PM1: admin/auditor/write MUST see all records unfiltered."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            session_dict = {"username": "admin", "permisos": ["*"], "rol": "admin"}

            result = get_errores(session=session_dict)

        assert result["status"] == "success"
        assert len(result["data"]["errores"]) == 3

    def test_facturador_filtered_to_medico_and_own(self):
        """PM1: facturador sees only médico-assigned + self-created records."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            # fact_1 creates records for themselves and sees médico records
            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = get_errores(session=session_dict)

        assert result["status"] == "success"
        errores = result["data"]["errores"]
        ids = [e["id"] for e in errores]
        # e2 (MED ICO, médico) + e3 (FACT ONE, created_by=fact_1) are visible
        # e1 (JUAN PEREZ, facturador, not created by fact_1) should be hidden
        assert "e2" in ids  # médico record
        assert "e3" in ids  # self-created
        assert "e1" not in ids  # another facturador, not self-created

    def test_medico_sees_only_self_assigned(self):
        """PM1: médico sees only self-assigned records (by full name match)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            session_dict = {
                "username": "med_1",
                "permisos": ["control_urgencias"],
                "rol": "medico",
                "primer_nombre": "MED",
                "apellido_1": "ICO",
            }

            result = get_errores(session=session_dict)

        assert result["status"] == "success"
        errores = result["data"]["errores"]
        ids = [e["id"] for e in errores]
        # Only e2 (MED ICO, self) should be visible
        assert ids == ["e2"]


class TestGetErroresPerRecordFlags:
    """Task 2.4: get_errores() adds per-record can_edit/can_delete flags (PM6)."""

    @staticmethod
    def _fake_records():
        return [
            {
                "id": "e1", "responsable": "MED ICO", "tipo_error": "X",
                "creado_en": "2026-01-01", "created_by": "med_1",
            },
        ]

    @staticmethod
    def _fake_users():
        return [
            {
                "username": "med_1", "rol": "medico", "permisos": [],
                "primer_nombre": "MED", "segundo_nombre": "", "apellido_1": "ICO", "apellido_2": "",
            },
            {
                "username": "fact_1", "rol": "facturador", "permisos": [],
                "primer_nombre": "FACT", "segundo_nombre": "", "apellido_1": "ONE", "apellido_2": "",
            },
        ]

    def test_admin_per_record_flags(self):
        """PM6: admin/auditor/write get can_edit:true, can_delete:true on all."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            session_dict = {"username": "admin", "permisos": ["*"], "rol": "admin"}

            result = get_errores(session=session_dict)

        errores = result["data"]["errores"]
        assert len(errores) == 1
        assert errores[0]["can_edit"] is True
        assert errores[0]["can_delete"] is True

    def test_facturador_on_medico_record_flags(self):
        """PM6: facturador on médico record → can_edit:true, can_delete:true."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = get_errores(session=session_dict)

        errores = result["data"]["errores"]
        assert len(errores) == 1
        assert errores[0]["can_edit"] is True
        assert errores[0]["can_delete"] is True

    def test_medico_on_own_record_flags(self):
        """PM6: médico on own record → can_edit:false, can_delete:false."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.listar_errores") as mock_list,
            patch("app.services.control_errores_service.list_users") as mock_users,
        ):
            mock_list.return_value = self._fake_records()
            mock_users.return_value = self._fake_users()

            session_dict = {
                "username": "med_1",
                "permisos": ["control_urgencias"],
                "rol": "medico",
                "primer_nombre": "MED",
                "apellido_1": "ICO",
            }

            result = get_errores(session=session_dict)

        errores = result["data"]["errores"]
        assert len(errores) == 1
        # PM6: médico has no full-edit capability (only partial estado/obs)
        assert errores[0]["can_edit"] is False
        assert errores[0]["can_delete"] is False


# =============================================================================
# Task 2.5: update_error() — _can_edit() ownership gate (R1/R16)
# =============================================================================


class TestUpdateErrorOwnershipGate:
    """Task 2.5: update_error() checks _can_edit() before field-level permission."""

    def test_facturador_full_write_on_medico_record(self):
        """R1: facturador on médico record MUST have full write (all fields)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r1", "responsable_rol": "MEDICO",
                "created_by": "dr_medico", "estado": "S",
            }
            mock_upd.return_value = {"id": "r1", "tipo_error": "X", "estado": "S"}

            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = update_error("r1", {"tipo_error": "X"}, session=session_dict)

        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_facturador_blocked_on_non_medico_record(self):
        """R1: facturador on non-médico (non-own) record → 403."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r2", "responsable_rol": "FACTURADOR",
                "created_by": "other_fact", "estado": "S",
            }
            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = update_error("r2", {"tipo_error": "X"}, session=session_dict)

        assert isinstance(result, tuple)
        assert result[1] == 403
        mock_upd.assert_not_called()

    def test_medico_partial_edit_on_own(self):
        """R1: médico on own record → partial edit (estado/obs) allowed."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r3", "responsable_rol": "MEDICO",
                "created_by": "dr_medico", "estado": "S",
            }
            mock_upd.return_value = {"id": "r3", "estado": "R"}

            session_dict = {
                "username": "dr_medico",
                "permisos": ["control_urgencias"],
                "rol": "medico",
            }

            result = update_error("r3", {"estado": "R"}, session=session_dict)

        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_medico_full_edit_blocked_on_own(self):
        """R1: médico on own record → full edit (non-estado/obs) blocked."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r4", "responsable_rol": "MEDICO",
                "created_by": "dr_medico", "estado": "S",
            }
            session_dict = {
                "username": "dr_medico",
                "permisos": ["control_urgencias"],
                "rol": "medico",
            }

            result = update_error("r4", {"tipo_error": "X"}, session=session_dict)

        assert isinstance(result, tuple)
        assert result[1] == 403
        mock_upd.assert_not_called()

    def test_admin_bypass_ownership_gate(self):
        """R2: admin/auditor/write MUST bypass all ownership checks."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            mock_get.return_value = {
                "id": "r5", "responsable_rol": "FACTURADOR",
                "created_by": "someone_else", "estado": "S",
            }
            mock_upd.return_value = {"id": "r5", "tipo_error": "Y"}

            session_dict = {
                "username": "admin_1",
                "permisos": ["*"],
                "rol": "admin",
            }

            result = update_error("r5", {"tipo_error": "Y"}, session=session_dict)

        assert result["status"] == "success"
        mock_upd.assert_called_once()


# =============================================================================
# Task 2.6: delete_error() — _can_delete() gate (R16/PM3)
# =============================================================================


class TestDeleteErrorOwnershipGate:
    """Task 2.6: delete_error() checks _can_delete() before deletion."""

    def test_admin_can_delete_any(self):
        """admin/auditor/write MUST be able to delete any record."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d1", "responsable_rol": "FACTURADOR",
                "created_by": "other", "estado": "S",
            }
            mock_del.return_value = True

            session_dict = {"username": "admin_1", "permisos": ["*"], "rol": "admin"}

            result = delete_error("d1", session=session_dict)

        assert result["status"] == "success"
        mock_del.assert_called_once()

    def test_facturador_can_delete_medico_record(self):
        """R16: facturador MUST be able to delete médico records."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d2", "responsable_rol": "MEDICO",
                "created_by": "dr_medico", "estado": "S",
            }
            mock_del.return_value = True

            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = delete_error("d2", session=session_dict)

        assert result["status"] == "success"
        mock_del.assert_called_once()

    def test_facturador_blocked_on_non_medico(self):
        """R16/PM3: facturador MUST be blocked on non-médico records."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d3", "responsable_rol": "FACTURADOR",
                "created_by": "other", "estado": "S",
            }
            session_dict = {
                "username": "fact_1",
                "permisos": ["control_urgencias"],
                "rol": "facturador",
            }

            result = delete_error("d3", session=session_dict)

        assert result["status"] == "error"
        assert result["errors"]
        mock_del.assert_not_called()

    def test_medico_cannot_delete(self):
        """R16/PM3: médico MUST always be blocked from deleting."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d4", "responsable_rol": "MEDICO",
                "created_by": "dr_medico", "estado": "S",
            }
            session_dict = {
                "username": "dr_medico",
                "permisos": ["control_urgencias"],
                "rol": "medico",
            }

            result = delete_error("d4", session=session_dict)

        assert result["status"] == "error"
        mock_del.assert_not_called()

    def test_backward_compat_delete_without_session(self):
        """delete_error() without session MUST fall back to flask.session."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {
                "id": "d5", "responsable_rol": "FACTURADOR",
                "created_by": "other", "estado": "S",
            }
            mock_del.return_value = True
            session["permisos"] = ["*"]
            session["rol"] = "admin"

            result = delete_error("d5")

        assert result["status"] == "success"
