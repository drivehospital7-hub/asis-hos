"""Strict TDD RED tests for the integration submission service (Phase 3).

The integration service validates a JSON schema, forces category
"Soportes de Carpeta", resolves responsible via existing coincidence logic,
and keeps validator (from token) separate from responsible. Each submission
creates a new record: duplicate submissions are allowed (no idempotency).
"""

from unittest.mock import patch

import json
from io import BytesIO

import pytest

from app.services.integration_service import submit

# Synthetic session as built by the bearer branch from the token
_VALIDATOR_SESSION = {
    "ce_authenticated": True,
    "username": "ana",
    "rol": "validador",
    "permisos": ["control_urgencias", "control_urgencias:write"],
    "primer_nombre": "Ana",
    "segundo_nombre": "",
    "apellido_1": "Valdez",
    "apellido_2": "",
}

VALID_PAYLOAD = {
    "factura": "FEV123",
    "observacion": "falta soporte",
    "responsable": "LORENY ESPAÑA",
    "nombres": "CARLOS PEREZ",
    "observacion_facturador": "",
}


@pytest.fixture(autouse=True)
def _default_validator_resolution(monkeypatch):
    """Default integration path: payload ``nombres`` resolves to a unique
    canonical validator identity ("carlos perez").

    Tests that exercise rejection (missing / no-match / ambiguous) override
    this with an explicit patch returning None or a side_effect.
    """
    monkeypatch.setattr(
        "app.services.integration_service._resolve_validador",
        lambda raw: "carlos perez",
    )


class TestSchemaValidation:
    def test_valid_payload_success(self):
        """Conforming payload → success envelope."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        assert envelope["errors"] == []
        assert envelope["data"]["error"]["id"] == "new-id"

    def test_missing_required_field_error(self):
        """Missing 'factura' → error envelope, nothing persisted."""
        payload = dict(VALID_PAYLOAD)
        del payload["factura"]
        with (
            patch("app.services.integration_service._persist") as mock_persist,
        ):
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert len(envelope["errors"]) > 0
        mock_persist.assert_not_called()

    def test_mistyped_field_error(self):
        """'factura' as non-string → error envelope."""
        payload = dict(VALID_PAYLOAD, factura=123)
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert len(envelope["errors"]) > 0
        mock_persist.assert_not_called()

    def test_unknown_fields_ignored(self):
        """Client-supplied tipo_error/validador/created_by MUST be ignored."""
        payload = dict(
            VALID_PAYLOAD,
            tipo_error="Factura Abierta",
            validador="hacker",
            created_by="hacker",
        )
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"


class TestForcedCategory:
    def test_category_forced_soportes_de_carpeta(self):
        """Record persisted with category 'Soportes de Carpeta'."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        assert call_data["tipo_error"] == "Soportes de Carpeta"

    def test_client_category_override_ignored(self):
        """A client-supplied different category is ignored and forced value stored."""
        payload = dict(VALID_PAYLOAD, tipo_error="Factura Abierta")
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            submit(payload, _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        assert call_data["tipo_error"] == "Soportes de Carpeta"


class TestResponsibleResolution:
    def test_matching_responsible_normalizes_to_db_user(self):
        """Raw responsible matching a DB user is resolved and persisted UPPERCASE."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="loreny españa",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        call_data = mock_persist.call_args.args[0]
        assert call_data["responsable"] == "LORENY ESPAÑA"

    def test_ambiguous_or_unmatched_responsible_rejected(self):
        """Raw responsible with no unique coincidence → rejected, nothing persisted."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value=None,
            ),
            patch("app.services.integration_service._persist") as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert len(envelope["errors"]) > 0
        mock_persist.assert_not_called()


class TestValidatorFromPayload:
    """Validator identity comes from payload ``nombres`` (resolved against the
    DB validator pool); ``created_by`` stays the token-owner username.

    Strict TDD RED: these tests replace the old token-derived validator tests
    and fail against the current _persist(session-derived) behavior.
    """

    def test_validator_resolved_from_payload_nombres(self):
        """Client-injected validador/created_by are stripped; the payload
        nombres is resolved and passed separately to _persist."""
        payload = dict(VALID_PAYLOAD, validador="hacker", created_by="hacker")
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="loreny españa",
            ),
            patch(
                "app.services.integration_service._resolve_validador",
                return_value="carlos perez",
            ) as mock_validador,
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            submit(payload, _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        # The client's validador/created_by are NOT forwarded
        assert "validador" not in call_data
        assert "created_by" not in call_data
        # The payload nombres drives the resolved validator identity
        assert mock_validador.call_args.args[0] == "CARLOS PEREZ"
        assert mock_persist.call_args.args[2] == "carlos perez"
        # created_by comes from the synthetic session (token owner), distinct
        # from the resolved validator
        sess = mock_persist.call_args.args[1]
        assert sess["username"] == "ana"
        # responsible stays a separate identity from validator (persisted UPPERCASE)
        assert call_data["responsable"] == "LORENY ESPAÑA"


class TestMissingNombres:
    """``nombres`` is required: single → 400 whole envelope; batch item
    lacking it → per-item error, other items continue (never structural)."""

    def test_single_missing_nombres_rejected(self):
        """Single payload without ``nombres`` → 400, nothing persisted."""
        payload = dict(VALID_PAYLOAD)
        del payload["nombres"]
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert any("nombres" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_item_missing_nombres_per_item_error(self):
        """A batch item without ``nombres`` is rejected per item; the other
        items of the batch still process."""
        batch = {
            "novedades": [
                # item 1: missing nombres
                {"factura": "FEV1", "observacion": "obs 1", "responsable": "LORENY ESPAÑA"},
                {"factura": "FEV2", "observacion": "obs 2", "responsable": "LORENY ESPAÑA", "nombres": "CARLOS PEREZ"},
            ]
        }
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._resolve_validador",
                side_effect=[None, "carlos perez"],
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "r2"},
            ) as mock_persist,
        ):
            envelope, status = submit(batch, _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        data = envelope["data"]
        assert data["procesadas"] == 1
        assert data["rechazadas"] == 1
        rejected, ok = data["resultados"]
        assert rejected["factura"] == "FEV1"
        assert rejected["status"] == "error"
        assert "Validador no resuelto" in rejected["motivo"]
        assert ok["factura"] == "FEV2"
        assert ok["status"] == "success"
        assert ok["error"]["id"] == "r2"
        # Only the valid item is persisted; the rejected one does not abort the batch
        mock_persist.assert_called_once()


class TestUnresolvableNombres:
    """``nombres`` with no unique validator coincidence → rejected
    (single: 400; batch: per-item error)."""

    def test_single_no_match_or_ambiguous_rejected(self):
        """Unmatched or ambiguous ``nombres`` → 400, nothing persisted."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._resolve_validador",
                return_value=None,
            ),
            patch("app.services.integration_service._persist") as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert any("Validador no resuelto" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_no_match_per_item_error(self):
        """A batch item whose ``nombres`` does not resolve → per-item error,
        the other items still process."""
        batch = {
            "novedades": [
                {"factura": "FEV1", "observacion": "obs 1", "responsable": "LORENY ESPAÑA", "nombres": "JUAN MARTINEZ"},
                {"factura": "FEV2", "observacion": "obs 2", "responsable": "LORENY ESPAÑA", "nombres": "CARLOS PEREZ"},
            ]
        }
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._resolve_validador",
                side_effect=[None, "carlos perez"],
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "r2"},
            ) as mock_persist,
        ):
            envelope, status = submit(batch, _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        data = envelope["data"]
        assert data["procesadas"] == 1
        assert data["rechazadas"] == 1
        rejected, ok = data["resultados"]
        assert rejected["factura"] == "FEV1"
        assert rejected["status"] == "error"
        assert "Validador no resuelto" in rejected["motivo"]
        assert ok["status"] == "success"
        mock_persist.assert_called_once()


class TestNoIdempotency:
    def test_submit_always_persists_new_record(self):
        """Each submit persists a new record (201) — duplicates are allowed."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        assert envelope["data"]["error"]["id"] == "new-id"
        mock_persist.assert_called_once()

    def test_idempotency_key_not_forwarded_to_persist(self):
        """Even if the client sends idempotency_key, it is not persisted."""
        payload = dict(VALID_PAYLOAD, idempotency_key="client-key")
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ) as mock_persist,
        ):
            submit(payload, _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        assert "idempotency_key" not in call_data

    def test_idempotency_key_not_required(self):
        """A payload without idempotency_key is valid (201)."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"


class TestAtomicPersistence:
    def test_persist_failure_returns_error(self):
        """A persistence (atomic write) failure → error envelope."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                side_effect=OSError("disk full"),
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 500
        assert envelope["status"] == "error"
        assert len(envelope["errors"]) > 0


class TestOptionalImage:
    def _image(self, filename="support.png"):
        image = BytesIO(b"image-data")
        image.name = filename
        return image

    def test_valid_image_is_saved_for_new_error(self):
        image = self._image()
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch("app.services.integration_service.errores_storage.validar_imagen", return_value=(True, "")) as validate,
            patch("app.services.integration_service.errores_storage.guardar_imagen", return_value=(True, "file_1.png")) as save,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image])

        assert status == 201
        assert envelope["status"] == "success"
        validate.assert_called_once_with(image)
        save.assert_called_once()
        assert save.call_args.args == ("new-id", image)
        assert save.call_args.kwargs["username"] == "ana"

    def test_guardar_imagen_recibe_username_de_sesion_sintetica(self):
        """FA-7: la integración pasa el username de la sesión sintética a guardar_imagen."""
        image = self._image()
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch("app.services.integration_service.errores_storage.validar_imagen", return_value=(True, "")),
            patch("app.services.integration_service.errores_storage.guardar_imagen", return_value=(True, "file_1.png")) as save,
        ):
            submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image])

        assert save.call_args.kwargs["username"] == "ana"

    def test_guardar_imagen_sin_sesion_username_none(self):
        """Sin sesión (None) → guardar_imagen recibe username=None (legacy)."""
        image = self._image()
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch("app.services.integration_service.errores_storage.validar_imagen", return_value=(True, "")),
            patch("app.services.integration_service.errores_storage.guardar_imagen", return_value=(True, "file_1.png")) as save,
        ):
            submit(dict(VALID_PAYLOAD), None, [image])

        assert save.call_args.kwargs.get("username") is None

    def test_missing_image_keeps_json_behavior(self):
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch("app.services.integration_service.errores_storage.guardar_imagen") as save,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope == {
            "status": "success",
            "data": {"error": {"id": "new-id"}},
            "errors": [],
        }
        save.assert_not_called()

    def test_invalid_image_is_rejected_before_persistence(self):
        image = self._image("support.exe")
        with (
            patch("app.services.integration_service.errores_storage.validar_imagen", return_value=(False, "Tipo no permitido: .exe")),
            patch("app.services.integration_service._persist") as persist,
):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image])

        assert status == 400
        assert envelope["status"] == "error"
        assert envelope["data"] == {}
        assert envelope["errors"] == ["Imagen inválida: Tipo no permitido: .exe"]
        persist.assert_not_called()

    def test_image_storage_failure_rolls_back_record(self):
        image = self._image()
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch("app.services.integration_service.errores_storage.validar_imagen", return_value=(True, "")),
            patch("app.services.integration_service.errores_storage.guardar_imagen", return_value=(False, "disk full")),
            patch("app.services.integration_service.errores_storage.eliminar_error", return_value=True) as delete,
):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image])

        assert status == 500
        assert envelope["status"] == "error"
        assert envelope["data"] == {}
        assert "disk full" in envelope["errors"][0]
        delete.assert_called_once_with("new-id")

    def test_multiple_valid_images_saved_in_order(self):
        image1 = self._image("a.png")
        image2 = self._image("b.png")
        image3 = self._image("c.png")
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch(
                "app.services.integration_service.errores_storage.validar_imagen",
                return_value=(True, ""),
            ) as validate,
            patch(
                "app.services.integration_service.errores_storage.guardar_imagen",
                side_effect=[(True, "file_1.png"), (True, "file_2.png"), (True, "file_3.png")],
            ) as save,
        ):
            envelope, status = submit(
                dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image1, image2, image3]
            )

        assert status == 201
        assert envelope["status"] == "success"
        assert validate.call_count == 3
        assert save.call_count == 3
        assert save.call_args_list[0].args == ("new-id", image1)
        assert save.call_args_list[1].args == ("new-id", image2)
        assert save.call_args_list[2].args == ("new-id", image3)
        assert all(
            c.kwargs.get("username") == "ana" for c in save.call_args_list
        )

    def test_more_than_max_images_rejected_before_persistence(self):
        images = [self._image(f"img_{i}.png") for i in range(4)]
        with (
            patch("app.services.integration_service._resolve_responsable") as resolve,
            patch("app.services.integration_service._persist") as persist,
            patch("app.services.integration_service.errores_storage.guardar_imagen") as save,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, images)

        assert status == 400
        assert envelope["status"] == "error"
        assert envelope["data"] == {}
        assert any("3" in e for e in envelope["errors"])
        resolve.assert_not_called()
        persist.assert_not_called()
        save.assert_not_called()

    def test_one_invalid_image_among_several_rejected_before_persistence(self):
        valid = self._image("valid.png")
        invalid = self._image("support.exe")
        with (
            patch(
                "app.services.integration_service.errores_storage.validar_imagen",
                side_effect=[(True, ""), (False, "Tipo no permitido: .exe")],
            ) as validate,
            patch("app.services.integration_service._persist") as persist,
            patch("app.services.integration_service.errores_storage.guardar_imagen") as save,
        ):
            envelope, status = submit(
                dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [valid, invalid]
            )

        assert status == 400
        assert envelope["status"] == "error"
        assert envelope["data"] == {}
        assert envelope["errors"] == ["Imagen inválida: Tipo no permitido: .exe"]
        assert validate.call_count == 2
        persist.assert_not_called()
        save.assert_not_called()

    def test_save_failure_midway_rolls_back_record(self):
        image1 = self._image("a.png")
        image2 = self._image("b.png")
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch(
                "app.services.integration_service.errores_storage.validar_imagen",
                return_value=(True, ""),
            ),
            patch(
                "app.services.integration_service.errores_storage.guardar_imagen",
                side_effect=[(True, "file_1.png"), (False, "disk full")],
            ) as save,
            patch("app.services.integration_service.errores_storage.eliminar_error", return_value=True) as delete,
        ):
            envelope, status = submit(
                dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image1, image2]
            )

        assert status == 500
        assert envelope["status"] == "error"
        assert envelope["data"] == {}
        assert "disk full" in envelope["errors"][0]
        assert "1 de 2" in envelope["errors"][0]
        assert save.call_count == 2
        delete.assert_called_once_with("new-id")

    def test_single_image_in_list_still_works(self):
        image = self._image()
        with (
            patch("app.services.integration_service._resolve_responsable", return_value="LORENY ESPAÑA"),
            patch("app.services.integration_service._persist", return_value={"id": "new-id"}),
            patch(
                "app.services.integration_service.errores_storage.validar_imagen",
                return_value=(True, ""),
            ),
            patch(
                "app.services.integration_service.errores_storage.guardar_imagen",
                return_value=(True, "file_1.png"),
            ) as save,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION, [image])

        assert status == 201
        assert envelope["status"] == "success"
        save.assert_called_once()
        assert save.call_args.args == ("new-id", image)
        assert save.call_args.kwargs.get("username") == "ana"


class TestBatchSubmit:
    """Primary contract: {"novedades": [...]} processes all items in one request
    and returns per-item results (HTTP 200 / status success)."""

    BATCH = {
        "novedades": [
            {"factura": "FEV1", "observacion": "falta soporte 1", "responsable": "LORENY ESPAÑA", "nombres": "CARLOS PEREZ"},
            {"factura": "FEV2", "observacion": "falta soporte 2", "responsable": "LORENY ESPAÑA", "nombres": "CARLOS PEREZ"},
        ]
    }

    def test_batch_all_success(self):
        """Whole valid batch → 200, procesadas=2, rechazadas=0, per-item results."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                side_effect=[{"id": "r1"}, {"id": "r2"}],
            ) as mock_persist,
        ):
            envelope, status = submit(dict(self.BATCH), _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        assert envelope["errors"] == []
        data = envelope["data"]
        assert data["procesadas"] == 2
        assert data["rechazadas"] == 0
        assert [r["factura"] for r in data["resultados"]] == ["FEV1", "FEV2"]
        assert all(r["status"] == "success" for r in data["resultados"])
        assert data["resultados"][0]["error"]["id"] == "r1"
        assert data["resultados"][1]["error"]["id"] == "r2"
        assert mock_persist.call_count == 2

    def test_batch_partial_failure_rejects_only_bad_item(self):
        """An unresolvable responsible rejects only ITS item (200, no rollback)."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                side_effect=["LORENY ESPAÑA", None],
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "r1"},
            ) as mock_persist,
        ):
            envelope, status = submit(dict(self.BATCH), _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        data = envelope["data"]
        assert data["procesadas"] == 1
        assert data["rechazadas"] == 1
        ok, rejected = data["resultados"]
        assert ok["factura"] == "FEV1"
        assert ok["status"] == "success"
        assert rejected["factura"] == "FEV2"
        assert rejected["status"] == "error"
        assert "Responsable no resuelto" in rejected["motivo"]
        # Only the valid item is persisted; the rejected one does not abort the batch
        mock_persist.assert_called_once()

    def test_batch_empty_list_rejected(self):
        """Empty 'novedades' list → 400 with a clear error, nothing persisted."""
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit({"novedades": []}, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert any("vacía" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_not_a_list_rejected(self):
        """'novedades' that is not a list → 400."""
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit({"novedades": {"factura": "FEV1"}}, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert any("lista" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_with_images_rejected(self):
        """Images attached to a batch payload → 400, batch never processed."""
        image = BytesIO(b"image-data")
        image.name = "support.png"
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit(
                dict(self.BATCH), _VALIDATOR_SESSION, [image]
            )

        assert status == 400
        assert envelope["status"] == "error"
        assert any("registro individual" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_item_missing_required_field_rejected(self):
        """An item missing a required field invalidates the whole batch → 400."""
        payload = {"novedades": [{"factura": "FEV1", "observacion": "obs"}]}
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        assert any("responsable" in e for e in envelope["errors"])
        mock_persist.assert_not_called()

    def test_batch_item_not_object_rejected(self):
        """An item that is not an object → 400."""
        with patch("app.services.integration_service._persist") as mock_persist:
            envelope, status = submit({"novedades": ["FEV1"]}, _VALIDATOR_SESSION)

        assert status == 400
        assert envelope["status"] == "error"
        mock_persist.assert_not_called()

    def test_batch_forces_category_per_item(self):
        """Every item is persisted with the forced category and UPPERCASE responsible."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="loreny españa",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            submit(dict(self.BATCH), _VALIDATOR_SESSION)

        assert mock_persist.call_count == 2
        for call in mock_persist.call_args_list:
            assert call.args[0]["tipo_error"] == "Soportes de Carpeta"
            assert call.args[0]["responsable"] == "LORENY ESPAÑA"

    def test_batch_persist_failure_rejects_only_that_item(self):
        """A persistence failure on one item rejects it without aborting the batch."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                side_effect=[{"id": "r1"}, OSError("disk full")],
            ),
        ):
            envelope, status = submit(dict(self.BATCH), _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        data = envelope["data"]
        assert data["procesadas"] == 1
        assert data["rechazadas"] == 1
        assert data["resultados"][1]["status"] == "error"
        assert "disk full" in data["resultados"][1]["motivo"]

    def test_legacy_single_item_still_supported(self):
        """The legacy single-item shape still returns 201/data.error."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        assert envelope["data"]["error"]["id"] == "new-id"


class TestDuplicateWarning:
    """Duplicate detection is a NON-BLOCKING warning: the record is always
    created; the response flags when the same category + factura already exists."""

    def test_single_warns_when_matching_record_exists(self):
        """Existing same category+factura → 201 + ya_existia True, still created."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ) as mock_persist,
            patch(
                "app.services.integration_service._contar_existentes",
                return_value=3,
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        assert envelope["data"]["error"]["ya_existia"] is True
        assert envelope["data"]["error"]["cantidad_existentes"] == 3
        mock_persist.assert_called_once()  # the record IS still created

    def test_single_no_flag_when_no_duplicate(self):
        """No matching record → success without the duplicate flag."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ),
            patch(
                "app.services.integration_service._contar_existentes",
                return_value=0,
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        assert "ya_existia" not in envelope["data"]["error"]
        assert "cantidad_existentes" not in envelope["data"]["error"]

    def test_batch_warns_when_matching_record_exists(self):
        """Batch item with existing match → result ya_existia True, still success."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                side_effect=[{"id": "r1"}, {"id": "r2"}],
            ),
            patch(
                "app.services.integration_service._contar_existentes",
                side_effect=[2, 0],
            ),
        ):
            envelope, status = submit(dict(TestBatchSubmit.BATCH), _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        assert envelope["data"]["procesadas"] == 2
        assert envelope["data"]["rechazadas"] == 0
        first, second = envelope["data"]["resultados"]
        assert first["status"] == "success"
        assert first["ya_existia"] is True
        assert first["cantidad_existentes"] == 2
        assert first["error"]["id"] == "r1"
        assert second["status"] == "success"
        assert "ya_existia" not in second

    def test_duplicate_check_runs_before_persist(self):
        """The existence check is consulted before the record is persisted."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "new-id"},
            ) as mock_persist,
            patch(
                "app.services.integration_service._contar_existentes",
                return_value=1,
            ) as mock_count,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert mock_count.call_count == 1
        # persist still ran (warning never blocks creation)
        mock_persist.assert_called_once()
        assert envelope["data"]["error"]["ya_existia"] is True


class TestDuplicateWarningStorage:
    """Real-JSON storage: the warning is computed against persisted records and
    never written back into the store (response-only decoration)."""

    @staticmethod
    def _patch_storage(tmp_path, errores_storage):
        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        return patch.object(errores_storage, "DATA_DIR", tmp_path), patch.object(
            errores_storage, "ERRORES_FILE", errores_file
        )

    def test_contar_duplicados_matches_category_and_factura(self, tmp_path):
        """contar_duplicados counts only records matching BOTH fields."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch:
            for factura in ["FEV-D1", "FEV-D1", "FEV-D2"]:
                errores_storage.crear_error(
                    tipo_error="Soportes de Carpeta",
                    factura=factura,
                    observacion="OBS",
                    estado="S",
                    responsable="LORENY ESPAÑA",
                )
            errores_storage.crear_error(
                tipo_error="Otros",
                factura="FEV-D1",
                observacion="OBS",
                estado="S",
                responsable="LORENY ESPAÑA",
            )

            assert errores_storage.contar_duplicados("Soportes de Carpeta", "FEV-D1") == 2
            assert errores_storage.contar_duplicados("Soportes de Carpeta", "FEV-D2") == 1
            assert errores_storage.contar_duplicados("Soportes de Carpeta", "FEV-D3") == 0
            # Same factura under a different category does not count as duplicate
            assert errores_storage.contar_duplicados("Otros", "FEV-D1") == 1

    def test_real_submit_warns_on_second_duplicate(self, tmp_path):
        """Second submit with the same category+factura → warning, no blocking."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        payload = dict(VALID_PAYLOAD, factura="fev-dedup-1")
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            first, status1 = submit(dict(payload), _VALIDATOR_SESSION)
            second, status2 = submit(dict(payload), _VALIDATOR_SESSION)

        assert status1 == 201
        assert status2 == 201  # duplicate does NOT block creation
        assert "ya_existia" not in first["data"]["error"]
        assert second["data"]["error"]["ya_existia"] is True
        assert second["data"]["error"]["cantidad_existentes"] == 1
        assert second["data"]["error"]["id"] != first["data"]["error"]["id"]

        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 2
        # The warning flag is response-only: never persisted to storage.
        assert all("ya_existia" not in record for record in data["errores"])
        # Existence check matched the uppercased (normalized) factura.
        assert all(record["factura"] == "FEV-DEDUP-1" for record in data["errores"])


class TestRealJsonPersistence:
    """End-to-end contract: real JSON storage, forced category, new record per submit."""

    def _patch_storage(self, tmp_path, errores_storage):
        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        # Patch BOTH DATA_DIR (temp file location) and ERRORES_FILE so the
        # atomic temp+rename stays on the same filesystem.
        return patch.object(errores_storage, "DATA_DIR", tmp_path), patch.object(
            errores_storage, "ERRORES_FILE", errores_file
        )

    def test_persists_record_with_forced_category(self, tmp_path):
        """Real submit persists to control_errores.json with forced category."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="loreny españa",
        ), patch(
            "app.services.integration_service._resolve_validador",
            return_value="carlos perez",
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"

        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 1
        record = data["errores"][0]
        # Forced category (client could not override — no tipo_error in payload)
        assert record["tipo_error"] == "Soportes de Carpeta"
        # Idempotency key must NOT be persisted
        assert "idempotency_key" not in record
        # Validator from the payload nombres, persisted UPPERCASE canonical
        assert record["validador"] == "CARLOS PEREZ"
        # created_by stays the token-owner username, distinct from the validator
        assert record["created_by"] == "ana"
        assert record["validador"] != record["created_by"]
        # Responsible normalized, UPPERCASE, and separate from validator
        assert record["responsable"] == "LORENY ESPAÑA"
        assert record["validador"] != record["responsable"]

    def test_duplicate_submissions_are_allowed(self, tmp_path):
        """A second submit creates a second record — duplicates are allowed."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            envelope1, status1 = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)
            envelope2, status2 = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status1 == 201
        assert status2 == 201  # duplicate allowed
        assert envelope2["data"]["error"]["id"] != envelope1["data"]["error"]["id"]

        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 2

    def test_client_category_override_rejected_in_real_storage(self, tmp_path):
        """A payload specifying a different category is ignored in real storage."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        payload = dict(VALID_PAYLOAD, tipo_error="Factura Abierta")
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 201
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert data["errores"][0]["tipo_error"] == "Soportes de Carpeta"


class TestConcurrentWrites:
    """The read-append-write MUST be atomic under the storage lock so two
    simultaneous submissions never lose an update (each produces its own
    persisted record, duplicates allowed)."""

    @staticmethod
    def _patch_storage(tmp_path, errores_storage):
        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        return patch.object(errores_storage, "DATA_DIR", tmp_path), patch.object(
            errores_storage, "ERRORES_FILE", errores_file
        )

    def test_two_simultaneous_submissions_persist_both(self, tmp_path):
        """Two threads submitting concurrently → both records persisted (no lost update)."""
        from app.utils import errores_storage
        import threading

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        results = []
        barrier = threading.Barrier(2)

        # Patches are entered ONCE in the main thread (patch contexts are not
        # thread-safe to enter/exit inside workers); workers only run submit,
        # which hits the module-level storage lock for the atomic read-append-write.
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            def worker():
                barrier.wait()
                envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)
                results.append((status, envelope["data"].get("error", {}).get("id")))

            threads = [threading.Thread(target=worker) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Both concurrent submissions persist their own record (duplicates allowed)
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 2
        assert len({r[1] for r in results}) == 2

    def test_crear_error_always_creates_new_record(self, tmp_path):
        """crear_error appends a new record each call (duplicates allowed)."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch:
            first = errores_storage.crear_error(
                tipo_error="Soportes de Carpeta",
                factura="FEV-C1",
                observacion="OBS 1",
                estado="S",
                responsable="LORENY ESPAÑA",
                validador="Ana Valdez",
                created_by="ana",
            )
            second = errores_storage.crear_error(
                tipo_error="Soportes de Carpeta",
                factura="FEV-C2",
                observacion="OBS 2",
                estado="S",
                responsable="LORENY ESPAÑA",
                validador="Ana Valdez",
                created_by="ana",
            )

        assert second["id"] != first["id"]
        # Neither record carries an idempotency_key
        assert "idempotency_key" not in first
        assert "idempotency_key" not in second
        # Both calls created a record
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 2


class TestOptionalRefactura:
    """R13: el endpoint LAN acepta refactura opcional y la persiste via crear_error."""

    def test_single_with_refactura_forwarded_to_persist(self):
        """Payload individual con refactura → record_data la incluye."""
        payload = dict(VALID_PAYLOAD, refactura="R-42")
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        call_data = mock_persist.call_args.args[0]
        assert call_data["refactura"] == "R-42"

    def test_single_without_refactura_stores_empty(self):
        """Payload individual sin refactura → record_data refactura='' (opcional)."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "x"},
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        call_data = mock_persist.call_args.args[0]
        assert call_data["refactura"] == ""

    def test_batch_item_with_refactura_forwarded_to_persist(self):
        """Item de lote con refactura → record_data la incluye."""
        batch = {
            "novedades": [
                {"factura": "FEV1", "observacion": "obs 1",
                 "responsable": "LORENY ESPAÑA", "nombres": "CARLOS PEREZ",
                 "refactura": "rf-batch-1"},
            ]
        }
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value={"id": "r1"},
            ) as mock_persist,
        ):
            envelope, status = submit(batch, _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        call_data = mock_persist.call_args.args[0]
        assert call_data["refactura"] == "rf-batch-1"

    def test_real_json_persists_refactura(self, tmp_path):
        """Storage real: submit con refactura → el registro persistido la lleva."""
        from app.utils import errores_storage

        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        payload = dict(VALID_PAYLOAD, refactura="R-99")
        with (
            patch.object(errores_storage, "DATA_DIR", tmp_path),
            patch.object(errores_storage, "ERRORES_FILE", errores_file),
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
        ):
            envelope, status = submit(payload, _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert data["errores"][0]["refactura"] == "R-99"

    def test_real_json_without_refactura_stores_empty(self, tmp_path):
        """Storage real: payload sin refactura → registro con refactura='' (opcional)."""
        from app.utils import errores_storage

        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        with (
            patch.object(errores_storage, "DATA_DIR", tmp_path),
            patch.object(errores_storage, "ERRORES_FILE", errores_file),
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert data["errores"][0]["refactura"] == ""
