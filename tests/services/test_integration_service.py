"""Strict TDD RED tests for the integration submission service (Phase 3).

The integration service validates a JSON schema, forces category
"Soportes de Carpeta", resolves responsible via existing coincidence logic,
and keeps validator (from token) separate from responsible. Each submission
creates a new record: duplicate submissions are allowed (no idempotency).
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
        """Raw responsible matching a DB user is resolved and stored."""
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
                return_value={"id": "x"},
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
        # Idempotency key must NOT be persisted
        assert "idempotency_key" not in record
        # Validator from the synthetic session (token owner)
        assert record["validador"] == "Ana Valdez"
        assert record["created_by"] == "ana"
        # Responsible normalized and separate from validator
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
