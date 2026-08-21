"""Strict TDD RED tests for the integration submission service (Phase 3).

The integration service validates a JSON schema, forces category
"Soportes de Carpeta", resolves responsible via existing coincidence logic,
keeps validator (from token) separate from responsible, and dedupes retries by
idempotency key under the JSON storage lock.
"""

from unittest.mock import patch

import json

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
    "idempotency_key": "key-abc",
    "observacion_facturador": "",
}


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
                return_value=({"id": "new-id"}, True),
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
                return_value=({"id": "x"}, True),
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
                return_value=({"id": "x"}, True),
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
                return_value=({"id": "x"}, True),
            ) as mock_persist,
        ):
            submit(payload, _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        assert call_data["tipo_error"] == "Soportes de Carpeta"


class TestResponsibleResolution:
    def test_matching_responsible_normalizes_to_db_user(self):
        """Raw responsible matching a DB user is resolved and stored."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value=({"id": "x"}, True),
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


class TestValidatorFromToken:
    def test_validator_from_session_not_payload(self):
        """Validator identity comes from the synthetic session, never payload."""
        # Client tries to inject validador/created_by — MUST be stripped
        payload = dict(VALID_PAYLOAD, validador="hacker", created_by="hacker")
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value=({"id": "x"}, True),
            ) as mock_persist,
        ):
            submit(payload, _VALIDATOR_SESSION)

        call_data = mock_persist.call_args.args[0]
        # The client's validador/created_by are NOT forwarded
        assert "validador" not in call_data
        assert "created_by" not in call_data
        # The token session (with validator identity) is passed separately
        sess = mock_persist.call_args.args[1]
        assert sess["primer_nombre"] == "Ana"
        assert sess["apellido_1"] == "Valdez"
        # responsible stays a separate identity from validator
        assert call_data["responsable"] == "LORENY ESPAÑA"


class TestIdempotency:
    def test_duplicate_key_returns_original_no_second_record(self):
        """A duplicate idempotency key → original record, created=False, 200."""
        original = {"id": "orig-id", "factura": "FEV123"}
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value=(original, False),
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 200
        assert envelope["status"] == "success"
        assert envelope["data"]["error"]["id"] == "orig-id"
        assert mock_persist.called

    def test_distinct_key_persists_new(self):
        """A new idempotency key persists a new record (created=True, 201)."""
        with (
            patch(
                "app.services.integration_service._resolve_responsable",
                return_value="LORENY ESPAÑA",
            ),
            patch(
                "app.services.integration_service._persist",
                return_value=({"id": "new-id"}, True),
            ) as mock_persist,
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"
        mock_persist.assert_called_once()


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


class TestRealJsonPersistence:
    """End-to-end contract: real JSON storage, forced category, idempotency."""

    def _patch_storage(self, tmp_path, errores_storage):
        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        # Patch BOTH DATA_DIR (temp file location) and ERRORES_FILE so the
        # atomic temp+rename stays on the same filesystem.
        return patch.object(errores_storage, "DATA_DIR", tmp_path), patch.object(
            errores_storage, "ERRORES_FILE", errores_file
        )

    def test_persists_record_with_forced_category_and_idempotency(self, tmp_path):
        """Real submit persists to control_errores.json with forced category + key."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            envelope, status = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status == 201
        assert envelope["status"] == "success"

        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 1
        record = data["errores"][0]
        # Forced category (client could not override — no tipo_error in payload)
        assert record["tipo_error"] == "Soportes de Carpeta"
        # Idempotency key persisted
        assert record["idempotency_key"] == VALID_PAYLOAD["idempotency_key"]
        # Validator from the synthetic session (token owner)
        assert record["validador"] == "Ana Valdez"
        assert record["created_by"] == "ana"
        # Responsible normalized and separate from validator
        assert record["responsable"] == "LORENY ESPAÑA"
        assert record["validador"] != record["responsable"]

    def test_duplicate_idempotency_key_no_second_record(self, tmp_path):
        """A second submit with the same key returns the original, no duplicate."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch, patch(
            "app.services.integration_service._resolve_responsable",
            return_value="LORENY ESPAÑA",
        ):
            envelope1, status1 = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)
            envelope2, status2 = submit(dict(VALID_PAYLOAD), _VALIDATOR_SESSION)

        assert status1 == 201
        assert status2 == 200  # deduped
        assert envelope2["data"]["error"]["id"] == envelope1["data"]["error"]["id"]

        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 1

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


class TestConcurrentIdempotency:
    """R4-1/R3-2: the check-then-write MUST be atomic under the storage lock so
    two simultaneous submissions with the same idempotency_key produce exactly
    one persisted record (no TOCTOU duplicate, no lost update)."""

    @staticmethod
    def _patch_storage(tmp_path, errores_storage):
        errores_file = tmp_path / "control_errores.json"
        errores_file.write_text(json.dumps({"errores": []}), encoding="utf-8")
        return patch.object(errores_storage, "DATA_DIR", tmp_path), patch.object(
            errores_storage, "ERRORES_FILE", errores_file
        )

    def test_two_simultaneous_same_key_submissions_persist_once(self, tmp_path):
        """Two threads submitting the SAME key concurrently → one persisted record."""
        from app.utils import errores_storage
        import threading

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        results = []
        barrier = threading.Barrier(2)

        # Patches are entered ONCE in the main thread (patch contexts are not
        # thread-safe to enter/exit inside workers); workers only run submit,
        # which hits the module-level storage lock for the atomic check-then-write.
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

        # At most one record may be persisted despite two concurrent submissions
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 1

    def test_atomic_operation_returns_existing_on_duplicate(self, tmp_path):
        """crear_error_idempotente returns (record, created=False) for a key that
        already exists, and (record, created=True) for a brand-new key."""
        from app.utils import errores_storage

        data_patch, file_patch = self._patch_storage(tmp_path, errores_storage)
        with data_patch, file_patch:
            first, created1 = errores_storage.crear_error_idempotente(
                idempotency_key="dup-key",
                tipo_error="Soportes de Carpeta",
                factura="FEV-C1",
                observacion="OBS 1",
                estado="S",
                responsable="LORENY ESPAÑA",
                validador="Ana Valdez",
                created_by="ana",
            )
            second, created2 = errores_storage.crear_error_idempotente(
                idempotency_key="dup-key",
                tipo_error="Soportes de Carpeta",
                factura="FEV-C2",
                observacion="OBS 2",
                estado="S",
                responsable="LORENY ESPAÑA",
                validador="Ana Valdez",
                created_by="ana",
            )

        assert created1 is True
        assert created2 is False
        assert second["id"] == first["id"]
        # The second call must NOT have created a second record
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        assert len(data["errores"]) == 1
