"""Tests for control_errores_service: update_error() permission logic.

Strict TDD: tests describe the NEW behavior (field-level permissions via
session["permisos"]) before production changes are made. These tests will
fail (RED) against the old code that uses session["ce_authenticated"].
"""

from unittest.mock import patch

import pytest
from flask import session

from app import create_app
from app.services.control_errores_service import update_error, add_error, get_errores, get_opciones
from app.services.control_errores_service import _resolve_responsable_identities
from app.utils.errores_storage import (
    listar_errores,
    crear_error,
    actualizar_error,
    normalizar_identidad,
)

# Application fixture for test request context
_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _fixture_errores():
    """Errores de prueba con responsables variados (incl. legacy sin created_by)."""
    return [
        {
            "id": "e1",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "LORENY ESPAÑA",
            "created_by": "val1",
            "creado_en": "2026-08-01T10:00:00",
        },
        {
            "id": "e2",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": " lorenY   españa ",
            "creado_en": "2026-08-02T10:00:00",
        },
        {
            "id": "e3",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "DANIELA PAEZ",
            "creado_en": "2026-08-03T10:00:00",
        },
        {
            "id": "e4",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "UNKNOWN PERSON",
            "creado_en": "2026-08-04T10:00:00",
        },
        {
            "id": "e5",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "CARLOS OMAR",
            "creado_en": "2026-08-05T10:00:00",
        },
        {
            "id": "e6",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": " carlos   meza ",
            "created_by": "val1",
            "creado_en": "2026-08-06T10:00:00",
        },
        {
            "id": "e7",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "CARLOS",
            "creado_en": "2026-08-07T10:00:00",
        },
        {
            "id": "e8",
            "tipo_error": "Otros",
            "estado": "S",
            "responsable": "CARLOS OMAR",
            "created_by": "val1",
            "creado_en": "2026-08-08T10:00:00",
        },
    ]


class TestGetErroresRoleVisibility:
    """Spec R1/R2/R4: role×ownership matrix on get_errores()."""

    def _call(self, sess_data, fixture):
        with (
            _APP.test_request_context(),
            patch("app.utils.errores_storage._leer_datos", return_value={"errores": fixture}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
        ):
            return get_errores(session=sess_data)

    # ── Facturador: own-only ──────────────────────────────────────────

    def test_facturador_sees_own_only(self):
        """Facturador con identidad LORENY ESPAÑA ve solo sus novedades."""
        sess = {
            "rol": "facturador",
            "username": "LORENYA",
            "primer_nombre": "LORENY ",
            "apellido_1": "ESPAÑA ",
            "permisos": ["control_urgencias"],
        }
        with patch(
            "app.services.control_errores_service.users_store.get_user",
            return_value={"primer_nombre": "LORENY ", "apellido_1": "ESPAÑA ", "rol": "facturador"},
        ):
            result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert ids == ["e2", "e1"]  # ambas normalizan a "loreny españa"
        assert "e3" not in ids
        assert "e4" not in ids

    def test_facturador_matches_new_canonical_and_legacy_alias(self):
        """New records need canonical equality; legacy records use aliases."""
        sess = {
            "rol": "facturador",
            "username": "OMARMF",
            "permisos": ["control_urgencias"],
        }
        with patch(
            "app.services.control_errores_service.users_store.get_user",
            return_value={
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Meza",
                "apellido_2": "Fernandez",
                "rol": "facturador",
            },
        ):
            result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert ids == ["e6", "e5"]
        assert "e8" not in ids

    def test_facturador_does_not_match_single_responsible_token(self):
        """A single common token must not expose a cross-user record."""
        sess = {"rol": "facturador", "username": "OMARMF"}
        with patch(
            "app.services.control_errores_service.users_store.get_user",
            return_value={
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Meza",
                "apellido_2": "Fernandez",
                "rol": "facturador",
            },
        ):
            result = self._call(sess, _fixture_errores())

        assert "e7" not in [e["id"] for e in result["data"]["errores"]]

    def test_facturador_unmatched_hidden(self):
        """Novedad cuyo responsable no matchea identidad DB → invisible al facturador."""
        sess = {
            "rol": "facturador",
            "username": "YULIETHDP",
            "primer_nombre": "DANIELA",
            "apellido_1": "PAEZ",
            "permisos": ["control_urgencias"],
        }
        with patch(
            "app.services.control_errores_service.users_store.get_user",
            return_value={"primer_nombre": "DANIELA", "apellido_1": "PAEZ", "rol": "facturador"},
        ):
            result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert ids == ["e3"]
        assert "e4" not in ids  # UNKNOWN PERSON no matchea a nadie

    def test_facturador_duplicate_identity_shared(self):
        """Dos facturadores con igual primer_nombre+apellido_1 comparten novedades."""
        fixture = _fixture_errores()
        for username in ("ANGIEC", "ANGIE2"):
            sess = {
                "rol": "facturador",
                "username": username,
                "permisos": ["control_urgencias"],
            }
            with patch(
                "app.services.control_errores_service.users_store.get_user",
                return_value={"primer_nombre": "ANGIE ", "apellido_1": "ARIAS ", "rol": "facturador"},
            ):
                # Insertar novedad de ANGIE ARIAS para que ambos la vean
                fixture_angie = fixture + [{
                    "id": "e5",
                    "tipo_error": "Otros",
                    "estado": "S",
                    "responsable": "ANGIE ARIAS",
                    "creado_en": "2026-08-05T10:00:00",
                }]
                result = self._call(sess, fixture_angie)

            ids = [e["id"] for e in result["data"]["errores"]]
            assert "e5" in ids

    def test_explicit_responsable_includes_legacy_db_identity_labels(self):
        """Explicit filters apply canonical matching to new records and aliases to legacy."""
        sess = {"rol": "validador", "username": "val1"}
        facturadores = [{
            "username": "OMARMF",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Omar",
            "apellido_1": "Meza",
            "apellido_2": "Fernandez",
            "nombre_completo": "CARLOS MEZA",
            "rol": "facturador",
        }]
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=facturadores,
        ), patch(
            "app.services.control_errores_service.listar_errores",
            wraps=listar_errores,
        ) as mock_listar, patch(
            "app.utils.errores_storage._leer_datos",
            return_value={"errores": _fixture_errores()},
        ), patch(
            "app.utils.errores_storage.obtener_imagenes_count",
            return_value=0,
        ):
            result = get_errores(responsable="CARLOS MEZA", session=sess)

        ids = [e["id"] for e in result["data"]["errores"]]
        assert ids == ["e6", "e5"]
        assert "e8" not in ids
        assert mock_listar.call_args.kwargs["responsable_identity"] == "carlos meza"
        assert mock_listar.call_args.kwargs["responsable_full_identity"] == (
            "carlos omar meza fernandez"
        )

    def test_explicit_responsable_does_not_match_single_token_or_other_user(self):
        """Explicit identity matching cannot broaden to a single token or another user."""
        sess = {"rol": "validador", "username": "val1"}
        facturadores = [{
            "username": "OMARMF",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Omar",
            "apellido_1": "Meza",
            "apellido_2": "Fernandez",
            "nombre_completo": "CARLOS MEZA",
            "rol": "facturador",
        }]
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=facturadores,
        ), patch(
            "app.utils.errores_storage._leer_datos",
            return_value={"errores": _fixture_errores()},
        ), patch(
            "app.utils.errores_storage.obtener_imagenes_count",
            return_value=0,
        ):
            result = get_errores(responsable="CARLOS MEZA", session=sess)

        ids = [e["id"] for e in result["data"]["errores"]]
        assert ids == ["e6", "e5"]
        assert "e7" not in ids
        assert "e3" not in ids

    def test_selected_permission_eligible_responsable_resolves(self):
        """Selected responsible resolution accepts explicit permission users."""
        eligible = [{
            "username": "VAL1",
            "primer_nombre": "Maria",
            "segundo_nombre": "Luisa",
            "apellido_1": "Gomez",
            "apellido_2": "Diaz",
            "nombre_completo": "MARIA GOMEZ",
            "rol": "validador",
            "permisos": ["responsable_facturacion"],
        }]
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=eligible,
            ),
            patch(
                "app.services.control_errores_service.listar_errores",
                return_value=[],
            ) as mock_listar,
        ):
            result = get_errores(responsable="MARIA GOMEZ", session={"rol": "validador"})

        assert result["status"] == "success"
        assert mock_listar.call_args.kwargs["responsable_identity"] == "maria gomez"

    def test_selected_validator_without_permission_is_not_resolved(self):
        """A validator absent from the eligible lookup cannot resolve."""
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=[],
            ),
            patch(
                "app.services.control_errores_service.listar_errores",
                return_value=[],
            ) as mock_listar,
        ):
            result = get_errores(responsable="MARIA GOMEZ", session={"rol": "validador"})

        assert result["status"] == "success"
        assert mock_listar.call_args.kwargs["responsable_identity"] is None

    # ── Validador / admin: all ────────────────────────────────────────

    def test_validador_sees_all(self):
        """Validador ve todas las novedades, incl. las no asignadas a facturadores."""
        sess = {"rol": "validador", "username": "val1", "permisos": ["control_urgencias:write"]}
        result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert set(ids) == {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"}

    def test_admin_sees_all(self):
        """Admin ve todas las novedades."""
        sess = {"rol": "admin", "username": "admin", "permisos": ["*"]}
        result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert set(ids) == {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"}

    def test_usuario_other_rol_sees_all(self):
        """Rol sin restricción (usuario/otro) → ve todo (sin filtro)."""
        sess = {"rol": "usuario", "username": "auditor", "permisos": ["control_urgencias"]}
        result = self._call(sess, _fixture_errores())

        ids = [e["id"] for e in result["data"]["errores"]]
        assert set(ids) == {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"}


class TestGetOpcionesDbOnly:
    """Spec R4: responsables solo desde DB facturadores, sin fallback."""

    def test_opciones_responsables_from_facturadores(self):
        """responsables = identidades de facturadores DB (primer_nombre + apellido_1)."""
        facturadores = [
            {"username": "ANGIEC", "primer_nombre": "ANGIE ", "apellido_1": "ARIAS ",
             "segundo_nombre": "CAROLINA", "apellido_2": "CULCHA ", "nombre_completo": "ANGIE ARIAS",
             "rol": "facturador"},
            {"username": "LORENYA", "primer_nombre": "LORENY ", "apellido_1": "ESPAÑA ",
             "segundo_nombre": "ALEJANDRA", "apellido_2": "DIAZ ", "nombre_completo": "LORENY ESPAÑA",
             "rol": "facturador"},
        ]
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=facturadores),
        ):
            opciones = get_opciones()

        assert opciones["status"] == "success"
        assert opciones["data"]["responsables"] == ["ANGIE ARIAS", "LORENY ESPAÑA"]
        assert "responsables_nombres_completos" not in opciones["data"]

    def test_opciones_empty_when_no_facturadores(self):
        """Sin facturadores DB → lista vacía (nunca hardcodeada)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=[]),
        ):
            opciones = get_opciones()

        assert opciones["status"] == "success"
        assert opciones["data"]["responsables"] == []

    def test_opciones_include_permission_eligible_users_only(self):
        """Options use the shared store eligibility rule, not validator role."""
        eligible = [{
            "username": "VAL1",
            "primer_nombre": "MARIA",
            "apellido_1": "GOMEZ",
            "nombre_completo": "MARIA GOMEZ",
            "rol": "validador",
            "permisos": ["responsable_facturacion"],
        }]
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=eligible,
            ),
        ):
            opciones = get_opciones()

        assert opciones["data"]["responsables"] == ["MARIA GOMEZ"]


class TestGetOpcionesAreas:
    """sdd Empieza: opciones agrega areas + responsables_detalle; responsables plano."""

    def test_opciones_adds_areas_and_responsables_detalle(self):
        """Payload aditivo: areas (7) + responsables_detalle; responsables sigue plano."""
        facturadores = [
            {"username": "ANGIEC", "primer_nombre": "ANGIE ", "apellido_1": "ARIAS ",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "ANGIE ARIAS",
             "rol": "facturador", "areas": ["urgencias", "odontologia"]},
            {"username": "LORENYA", "primer_nombre": "LORENY ", "apellido_1": "ESPAÑA ",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "LORENY ESPAÑA",
             "rol": "facturador", "areas": []},
        ]
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=facturadores),
        ):
            opciones = get_opciones()

        assert opciones["status"] == "success"
        data = opciones["data"]
        # responsables sigue plano (contrato existente)
        assert data["responsables"] == ["ANGIE ARIAS", "LORENY ESPAÑA"]
        # areas: SOLO las 4 canónicas (sin legacy selectable)
        assert [a["slug"] for a in data["areas"]] == [
            "urgencias", "ambulatoria", "extramural", "odontologia",
        ]
        assert all(
            a["slug"] not in {"equipos_basicos", "cruce_facturas", "derechos"}
            for a in data["areas"]
        )
        assert data["areas"][0] == {"slug": "urgencias", "label": "Urgencias"}
        # responsables_detalle: nombre → areas
        detalle = {d["nombre_completo"]: d["areas"] for d in data["responsables_detalle"]}
        assert detalle == {
            "ANGIE ARIAS": ["urgencias", "odontologia"],
            "LORENY ESPAÑA": [],
        }

    def test_opciones_flat_fallback_when_areas_missing(self):
        """Facturadores sin key 'areas' → detalle con listas vacías (rollout-safe)."""
        facturadores = [
            {"username": "ANGIEC", "primer_nombre": "ANGIE ", "apellido_1": "ARIAS ",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "ANGIE ARIAS",
             "rol": "facturador"},
        ]
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores",
                  return_value=facturadores),
        ):
            opciones = get_opciones()

        assert opciones["data"]["responsables"] == ["ANGIE ARIAS"]
        assert opciones["data"]["responsables_detalle"] == [
            {
                "nombre_completo": "ANGIE ARIAS",
                "identidad_completa": "ANGIE ARIAS",
                "areas": [],
            }
        ]


class TestGetErroresAreaFilter:
    """sdd Empieza: get_errores(area=) post-filtra por área (aditivo)."""

    _SESS = {"rol": "validador", "username": "val1"}

    def _call(self, area=None, responsable=None):
        with (
            _APP.test_request_context(),
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": _fixture_errores()}),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
        ):
            return get_errores(area=area, responsable=responsable, session=self._SESS)

    def _facturadores(self):
        return [
            {"username": "LORENYA", "primer_nombre": "LORENY", "apellido_1": "ESPAÑA",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "LORENY ESPAÑA",
             "rol": "facturador", "areas": ["urgencias"]},
            {"username": "DANIELA", "primer_nombre": "DANIELA", "apellido_1": "PAEZ",
             "segundo_nombre": "", "apellido_2": "", "nombre_completo": "DANIELA PAEZ",
             "rol": "facturador", "areas": ["ambulatoria"]},
        ]

    def test_area_filter_matches_only_area_users(self):
        """area=urgencias → solo novedades de responsables con esa área."""
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=self._facturadores(),
        ):
            result = self._call(area="urgencias")

        ids = [e["id"] for e in result["data"]["errores"]]
        # creado_en descendente: e2 (08-02) antes que e1 (08-01)
        assert ids == ["e2", "e1"]  # LORENY ESPAÑA + alias legacy
        assert "e3" not in ids      # DANIELA PAEZ no es de urgencias

    def test_area_filter_and_composes_with_responsable(self):
        """area AND responsable: responsables de otra área quedan excluidos."""
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=self._facturadores(),
        ):
            result = self._call(area="urgencias", responsable="DANIELA PAEZ")

        assert result["data"]["errores"] == []  # DANIELA no pertenece a urgencias

    def test_area_invalid_slug_is_noop(self):
        """Slug inválido → sin filtro (se devuelven todas las novedades)."""
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=self._facturadores(),
        ):
            result = self._call(area="no_existe")

        ids = {e["id"] for e in result["data"]["errores"]}
        assert ids == {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"}

    def test_area_valid_slug_zero_users_empty(self):
        """Área válida sin usuarios → resultado vacío (no-op NO es vacío)."""
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=self._facturadores(),
        ):
            result = self._call(area="extramural")

        assert result["data"]["errores"] == []

    def test_area_none_no_filter(self):
        """Sin área → se devuelven todas las novedades."""
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=self._facturadores(),
        ):
            result = self._call()

        ids = {e["id"] for e in result["data"]["errores"]}
        assert ids == {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"}


class TestAddErrorAudit:
    """Spec R5: created_by automático desde la sesión (auditoría)."""

    def test_add_error_canonicalizes_cronograma_display_value(self):
        """A unique display alias is persisted as the registered identity."""
        facturadores = [{
            "username": "OMARMF",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Omar",
            "apellido_1": "Meza",
            "apellido_2": "Fernandez",
            "nombre_completo": "CARLOS MEZA",
            "rol": "facturador",
        }]
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=facturadores,
            ),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "new-error"}
            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "CARLOS OMAR",
            }, session={"username": "val1"})

        assert mock_crear.call_args.args[4] == "CARLOS MEZA"

    def test_canonicalized_responsable_matches_existing_filter(self):
        """Canonical storage remains discoverable through the selector filter."""
        facturadores = [{
            "username": "OMARMF",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Omar",
            "apellido_1": "Meza",
            "apellido_2": "Fernandez",
            "nombre_completo": "CARLOS MEZA",
            "rol": "facturador",
        }]
        stored = [{
            "id": "canonical-error",
            "tipo_error": "OTROS",
            "estado": "S",
            "responsable": "CARLOS MEZA",
            "created_by": "val1",
            "creado_en": "2026-08-12T10:00:00",
        }]
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=facturadores,
            ),
            patch(
                "app.utils.errores_storage._leer_datos",
                return_value={"errores": stored},
            ),
            patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0),
        ):
            result = get_errores(
                responsable="CARLOS MEZA",
                session={"rol": "validador", "username": "val1"},
            )

        assert [error["id"] for error in result["data"]["errores"]] == [
            "canonical-error"
        ]

    def test_add_error_sets_created_by_from_session(self):
        """add_error() pasa created_by = username de sesión a crear_error()."""
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=[],
            ),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            sess = {"username": "val1", "rol": "validador",
                    "permisos": ["control_urgencias:write"],
                    "primer_nombre": "Maria", "apellido_1": "Gomez"}

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "LORENY ESPAÑA",
                "observacion": "test",
            }, session=sess)

            mock_crear.assert_called_once()
            assert mock_crear.call_args.kwargs.get("created_by") == "val1"

    def test_add_error_ignores_client_created_by(self):
        """created_by del payload del cliente se ignora; manda la sesión."""
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=[],
            ),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            sess = {"username": "val1", "rol": "validador",
                    "permisos": ["control_urgencias:write"]}

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "LORENY ESPAÑA",
                "observacion": "test",
                "created_by": "hacker",
            }, session=sess)

            assert mock_crear.call_args.kwargs.get("created_by") == "val1"


class TestNormalizarIdentidad:
    """Identity normalization is case-insensitive, accent-insensitive, and compact.

    normalizar_identidad(s) = casefold + accent removal + whitespace collapse.
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("LORENY ESPAÑA", "loreny espana"),
            (" lorenY   españa ", "loreny espana"),
            ("LORENY  ESPAÑA", "loreny espana"),  # doble espacio
            ("LORENY DEL CARMEN ESPAÑA RIVERA", "loreny del carmen espana rivera"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_normaliza_case_y_espacios(self, raw, expected):
        """Caso y espacios colapsados; None/empty → vacío."""
        assert normalizar_identidad(raw) == expected

    def test_normalizar_identidad_exists(self):
        """normalizar_identidad está disponible en errores_storage."""
        assert callable(normalizar_identidad)


class TestResponsibleIdentityResolution:
    """Responsible aliases resolve safely against eligible users."""

    def test_exact_canonical_precedes_ambiguous_full_name_alias(self):
        """An exact selector identity wins over a competing full-name subset."""
        facturadores = [
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Meza",
                "apellido_2": "Fernandez",
            },
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "Meza",
                "apellido_1": "Omar",
                "apellido_2": "Lopez",
            },
        ]
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=facturadores,
        ):
            result = _resolve_responsable_identities("CARLOS MEZA")

        assert result == ("carlos meza", "carlos omar meza fernandez")

    def test_ambiguous_alias_returns_none(self):
        """An alias shared by eligible users is not assigned arbitrarily."""
        facturadores = [
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Meza",
                "apellido_2": "Fernandez",
            },
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Perez",
                "apellido_2": "Lopez",
            },
        ]
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=facturadores,
        ):
            result = _resolve_responsable_identities("CARLOS OMAR")

        assert result is None

    def test_highest_full_identity_token_score_wins(self):
        """The most coincident full DB identity resolves canonically."""
        facturadores = [
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "Omar",
                "apellido_1": "Meza",
                "apellido_2": "Fernandez",
            },
            {
                "primer_nombre": "Carlos",
                "segundo_nombre": "",
                "apellido_1": "Meza",
                "apellido_2": "Lopez",
            },
        ]
        with patch(
            "app.services.control_errores_service.users_store.get_facturadores",
            return_value=facturadores,
        ):
            result = _resolve_responsable_identities(" CÁRLOS   OMAR ")

        assert result == ("carlos meza", "carlos omar meza fernandez")


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

    def test_update_error_canonicalizes_display_responsable(self):
        """Update passes a unique display alias to storage as canonical identity."""
        facturadores = [{
            "primer_nombre": "Carlos",
            "segundo_nombre": "Omar",
            "apellido_1": "Meza",
            "apellido_2": "Fernandez",
        }]
        with (
            _APP.test_request_context(),
            patch(
                "app.services.control_errores_service.users_store.get_facturadores",
                return_value=facturadores,
            ),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias:write"]
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "CARLOS MEZA"}

            result = update_error("test-1", {"responsable": "CARLOS OMAR"})

        assert result["status"] == "success"
        assert mock_upd.call_args.kwargs["responsable"] == "CARLOS MEZA"

    # ── Partial write (control_urgencias) — allowed fields ───────────

    def test_limited_allowed_estado(self):
        """User with 'control_urgencias' MUST be allowed to update 'estado'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "estado": "R"}

            result = update_error("test-1", {"estado": "R"})

        assert result["status"] == "success"
        assert result["data"]["error"]["estado"] == "R"
        mock_upd.assert_called_once()

    def test_limited_allowed_observacion_facturador(self):
        """User with 'control_urgencias' MUST be allowed to update 'observacion_facturador'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "observacion_facturador": "Ok"}

            result = update_error("test-1", {"observacion_facturador": "Ok"})

        assert result["status"] == "success"
        assert result["data"]["error"]["observacion_facturador"] == "Ok"
        mock_upd.assert_called_once()

    # ── Partial write — prohibited fields ────────────────────────────

    def test_limited_rejects_prohibited_field(self):
        """User with 'control_urgencias' MUST get 403 for 'tipo_error'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"tipo_error": "X"})

        # Expect a tuple (dict, 403)
        assert isinstance(result, tuple)
        assert result[1] == 403
        assert result[0]["status"] == "error"
        assert "tipo_error" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_mixed_payload(self):
        """User with 'control_urgencias' MUST reject payload with mixed allowed+prohibited."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"estado": "R", "responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "responsable" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_observacion(self):
        """User with 'control_urgencias' MUST NOT edit 'observacion' directly."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

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
        """No permisos in session MUST restrict to estado/observacion_facturador."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["ce_authenticated"] = True
            # No session["permisos"] set — key doesn't exist
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "responsable" in result[0]["errors"][0]
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
        ):
            session["primer_nombre"] = "Juan"
            session["apellido_1"] = "Pérez"

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
        ):
            session["primer_nombre"] = "Maria"
            session["apellido_1"] = "Gomez"

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
        ):
            # No session keys set — should fall back to empty
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
