"""RED tests: scoped (facturador) attachment storage for control de errores.

Strict TDD — these tests describe the NEW scoped behavior from the delta spec
(FA-1/FA-5/D1/D6/D7/R1/R2) and FAIL against the current storage:

- ``guardar_imagen`` has no ``scope`` parameter (TypeError → RED)
- no ``{id}/facturador`` directory, no per-scope max-3
- ``eliminar_imagen`` unlinks any filename without a listing check (R1)
- ``listar_errores`` does not enrich ``imagenes_facturador_count`` (FA-5)

Storage tests patch ``IMAGENES_PATH`` to a tmp dir; no real app data is touched.
"""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import patch

import pytest

from app.utils import errores_storage
from app.services.control_errores_service import (
    get_imagenes,
    upload_imagen,
    delete_imagen,
)


@pytest.fixture
def tmp_imagenes(tmp_path, monkeypatch):
    """Apunta IMAGENES_PATH a un directorio temporal."""
    monkeypatch.setattr(errores_storage, "IMAGENES_PATH", tmp_path / "imagenes")
    return tmp_path / "imagenes"


class _FakeFile:
    """File-like mínimo para guardar_imagen/validar_imagen (sufijo + bytes)."""

    def __init__(self, filename: str, content: bytes = b"data"):
        self.filename = filename
        self._content = content
        self._pos = 0

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 2:  # SEEK_END → simula medir tamaño
            self._pos = len(self._content) + offset
        else:
            self._pos = offset
        return self._pos

    def tell(self) -> int:
        return self._pos

    def read(self, size: int = -1) -> bytes:
        data = self._content[self._pos :]
        self._pos = len(self._content)
        return data


def _png() -> _FakeFile:
    return _FakeFile("captura.png", b"\x89PNG\r\n\x1a\nfake-png")


# =============================================================================
# FA-1: scoped storage + per-scope max 3 (tasks 1.1, 1.2)
# =============================================================================


class TestScopedSave:
    """FA-1: facturador uploads land in {id}/facturador/, observación untouched."""

    def test_guardar_facturador_scope_saves_scoped_dir(self, tmp_imagenes):
        """Scoped save → {id}/facturador/file_1.png; observación sin archivo."""
        ok, name = errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        assert ok is True
        assert name == "file_1.png"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()
        # Observación (default scope) NO debe tener el archivo
        assert not (tmp_imagenes / "e-1" / "file_1.png").exists()

    def test_guardar_default_scope_saves_observacion_dir(self, tmp_imagenes):
        """Default scope conserva el comportamiento legacy (observación)."""
        ok, name = errores_storage.guardar_imagen("e-1", _png())
        assert ok is True
        assert name == "file_1.png"
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()
        assert not (tmp_imagenes / "e-1" / "facturador").exists()

    def test_listar_imagenes_scope_aisla_observacion(self, tmp_imagenes):
        """M-1: el listado de observación excluye facturador/ y viceversa.

        Los archivos se nombran ``file_N{ext}`` POR scope (FA-1): el nombre
        original no se conserva, así que el aislamiento se prueba con
        extensiones distintas y nombres file_N por scope.
        """
        errores_storage.guardar_imagen("e-1", _FakeFile("obs.png"))
        errores_storage.guardar_imagen("e-1", _FakeFile("fac.jpg"), scope="facturador")
        assert errores_storage.listar_imagenes("e-1") == ["file_1.png"]
        assert errores_storage.listar_imagenes("e-1", "facturador") == ["file_1.jpg"]

    def test_obtener_count_por_scope(self, tmp_imagenes):
        """Counts por scope son independientes."""
        errores_storage.guardar_imagen("e-1", _FakeFile("a.png"))
        errores_storage.guardar_imagen("e-1", _FakeFile("b.png"), scope="facturador")
        assert errores_storage.obtener_imagenes_count("e-1") == 1
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 1


class TestMax3PerScope:
    """FA-1: max 3 se aplica POR scope, no al registro completo."""

    def test_max_3_por_scope_aislado(self, tmp_imagenes):
        """Observación llena (3) no bloquea el cupo de facturador."""
        for _ in range(3):
            ok, _ = errores_storage.guardar_imagen("e-1", _png())
            assert ok is True
        for _ in range(3):
            ok, _ = errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
            assert ok is True
        # 4to en facturador → rechazado, nada escrito
        ok, err = errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        assert ok is False
        assert "Máximo" in err
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 3

    def test_max_3_facturador_lleno_no_bloquea_observacion(self, tmp_imagenes):
        """Facturador lleno (3) no bloquea el cupo de observación."""
        for _ in range(3):
            errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        ok, _ = errores_storage.guardar_imagen("e-1", _png())
        assert ok is True
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 3
        assert errores_storage.obtener_imagenes_count("e-1") == 1

    def test_concurrent_uploads_allocate_unique_names_and_respect_quota(self, tmp_imagenes):
        """Concurrent uploads cannot overwrite or exceed the per-scope quota."""
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(
                lambda i: errores_storage.guardar_imagen(
                    "e-1", _FakeFile(f"upload-{i}.png", bytes([i])), scope="facturador"
                ), range(8)
            ))
        successful = [name for ok, name in results if ok]
        assert len(successful) == 3
        assert len(set(successful)) == 3
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 3


class TestEliminarErrorAmbosScopes:
    """D7: eliminar_error remueve {id}/ completo (ambos scopes)."""

    def test_eliminar_error_removes_both_scopes(self, tmp_imagenes):
        errores_storage.guardar_imagen("e-1", _png())
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        with (
            patch(
                "app.utils.errores_storage._leer_datos",
                return_value={"errores": [{"id": "e-1"}]},
            ),
            patch("app.utils.errores_storage._escribir_datos"),
        ):
            assert errores_storage.eliminar_error("e-1") is True
        assert not (tmp_imagenes / "e-1").exists()


# =============================================================================
# Threat matrix: executable files + scope routing (tasks 1.2)
# =============================================================================


class TestThreats:
    """Executable-file rejection and scope allowlist (R2)."""

    def test_guardar_facturador_rechaza_exe(self, tmp_imagenes):
        """.exe en scope facturador → rechazado, count 0, nada escrito."""
        ok, err = errores_storage.guardar_imagen(
            "e-1", _FakeFile("malware.exe"), scope="facturador"
        )
        assert ok is False
        assert "Tipo no permitido" in err
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 0
        assert not (tmp_imagenes / "e-1" / "facturador").exists()

    def test_get_imagenes_dir_scope_invalido_raise_valueerror(self, tmp_imagenes):
        """Scope fuera del allowlist → ValueError (backstop de R2)."""
        with pytest.raises(ValueError):
            errores_storage._get_imagenes_dir("e-1", "bogus")
        with pytest.raises(ValueError):
            errores_storage._get_imagenes_dir("e-1", "../escape")

    def test_get_imagenes_dir_rejects_invalid_error_id(self, tmp_imagenes):
        with pytest.raises(ValueError):
            errores_storage._get_imagenes_dir("..", "facturador")

    def test_routes_reject_invalid_error_id_before_listing_or_serving(self, app_client, monkeypatch):
        _login(app_client, ["control_urgencias:write"])
        monkeypatch.setattr(errores_storage, "listar_imagenes", lambda *args: pytest.fail("listed"))
        for url in (
            "/api/control-errores/%2E%2E/imagenes",
            "/api/control-errores/%2E%2E/imagenes/file_1.png",
        ):
            response = app_client.get(url)
            assert response.status_code == 404
        response = app_client.delete(
            "/api/control-errores/%2E%2E/imagenes/?filename=file_1.png"
        )
        assert response.status_code == 404


# =============================================================================
# R1: delete-side listing check (tasks 1.3)
# =============================================================================


class TestEliminarImagenScope:
    """R1: eliminar_imagen exige filename ∈ listar_imagenes(id, scope)."""

    def test_eliminar_imagen_scope_rechaza_path_trick(self, tmp_imagenes):
        """DELETE scoped '../file_1.png' → rechazado; archivo intacto."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        ok, _ = errores_storage.eliminar_imagen(
            "e-1", "../file_1.png", scope="facturador"
        )
        assert ok is False
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_eliminar_imagen_scope_rechaza_no_listado(self, tmp_imagenes):
        """DELETE de nombre no listado → rechazado; archivo listado intacto."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        ok, _ = errores_storage.eliminar_imagen(
            "e-1", "no_listado.png", scope="facturador"
        )
        assert ok is False
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_eliminar_imagen_scope_borra_archivo_listado(self, tmp_imagenes):
        """DELETE de archivo listado → borrado; observación no se toca."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen("e-1", _png())
        ok, err = errores_storage.eliminar_imagen(
            "e-1", "file_1.png", scope="facturador"
        )
        assert ok is True
        assert err == ""
        assert not (tmp_imagenes / "e-1" / "facturador" / "file_1.png").exists()
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()  # observación intacta


# =============================================================================
# FA-5: listar_errores enrichment (tasks 1.4)
# =============================================================================


class TestListarErroresEnrichment:
    """D6: listar_errores enriquece imagenes_facturador_count (aditivo)."""

    def test_listar_errores_enriquece_imagenes_facturador_count(self, tmp_imagenes):
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen("e-1", _png())  # observación
        with patch(
            "app.utils.errores_storage._leer_datos",
            return_value={"errores": [{"id": "e-1", "creado_en": "2026-08-01T10:00:00"}]},
        ):
            errores = errores_storage.listar_errores()
        assert errores[0]["imagenes_facturador_count"] == 2
        assert errores[0]["imagenes_count"] == 1  # observación sin regresión


# =============================================================================
# FA-7/R3: sidecar de ownership por scope (tasks 1.1, 1.2)
# =============================================================================


class TestOwnerSidecar:
    """FA-7: guardar_imagen registra al subidor en sidecar por scope.

    El sidecar ``.owner.json`` es invisible: no cuenta para count/cupo, no
    se lista, no se sirve (filtro dotfiles en listar_imagenes, R3).
    """

    def test_obtener_uploader_legacy_none(self, tmp_imagenes):
        """Adjunto previo sin sidecar → obtener_uploader devuelve None."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        assert errores_storage.obtener_uploader("e-1", "file_1.png", scope="facturador") is None

    def test_guardar_con_username_registra_owner(self, tmp_imagenes):
        """guardar_imagen(..., username="u") escribe sidecar {file_1.png: u}."""
        ok, name = errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="urgencias"
        )
        assert ok is True
        assert name == "file_1.png"
        sidecar = tmp_imagenes / "e-1" / "facturador" / ".owner.json"
        assert sidecar.is_file()
        import json
        assert json.loads(sidecar.read_text()) == {"file_1.png": "urgencias"}
        assert errores_storage.obtener_uploader(
            "e-1", "file_1.png", scope="facturador"
        ) == "urgencias"

    def test_owner_registrado_por_scope(self, tmp_imagenes):
        """El sidecar de observación y el de facturador son independientes."""
        errores_storage.guardar_imagen("e-1", _png(), username="obs")
        errores_storage.guardar_imagen(
            "e-1", _FakeFile("fac.jpg"), scope="facturador", username="fac"
        )
        assert errores_storage.obtener_uploader("e-1", "file_1.png") == "obs"
        assert errores_storage.obtener_uploader(
            "e-1", "file_1.jpg", scope="facturador"
        ) == "fac"

    def test_guardar_sin_username_no_crea_sidecar(self, tmp_imagenes):
        """Sin username → no se escribe sidecar (compat legacy, FA-7)."""
        ok, name = errores_storage.guardar_imagen("e-1", _png())
        assert ok is True
        assert not (tmp_imagenes / "e-1" / ".owner.json").exists()
        assert errores_storage.obtener_uploader("e-1", name) is None

    def test_listar_imagenes_excluye_sidecar(self, tmp_imagenes):
        """listar_imagenes filtra dotfiles → count sin sidecar (R3/FA-7)."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen(
            "e-1", _FakeFile("b.png"), scope="facturador", username="u"
        )
        # sidecar presente (1 guardado con username) → el dotfile NO se lista
        listing = errores_storage.listar_imagenes("e-1", "facturador")
        assert ".owner.json" not in listing
        assert listing == ["file_1.png", "file_2.png"]
        assert errores_storage.obtener_imagenes_count("e-1", "facturador") == 2

    def test_eliminar_imagen_limpia_entrada_sidecar(self, tmp_imagenes):
        """eliminar_imagen borra la entrada del sidecar (FA-7/D10)."""
        errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="u"
        )
        assert errores_storage.obtener_uploader(
            "e-1", "file_1.png", scope="facturador"
        ) == "u"
        ok, err = errores_storage.eliminar_imagen(
            "e-1", "file_1.png", scope="facturador"
        )
        assert ok is True
        assert err == ""
        assert not (tmp_imagenes / "e-1" / "facturador" / "file_1.png").exists()
        assert errores_storage.obtener_uploader(
            "e-1", "file_1.png", scope="facturador"
        ) is None

    def test_eliminar_carpeta_imagenes_incluye_sidecar(self, tmp_imagenes):
        """_eliminar_carpeta_imagenes (rmtree) remueve también el sidecar."""
        errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="u"
        )
        assert (tmp_imagenes / "e-1" / "facturador" / ".owner.json").is_file()
        errores_storage._eliminar_carpeta_imagenes("e-1")
        assert not (tmp_imagenes / "e-1").exists()


# =============================================================================
# Service: scope threading get/upload/delete_imagen (tasks 1.4, 3.1)
# =============================================================================


class TestServiceScope:
    """3.1/R4: el servicio reenvía scope a storage con default ""."""

    def test_get_imagenes_scope_passthrough(self):
        """get_imagenes(id, scope) delega el scope a listar/count."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ) as mock_list,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value=None,
            ),
        ):
            result = get_imagenes("e-1", scope="facturador")

        assert result["status"] == "success"
        assert result["data"] == {
            "imagenes": [{"filename": "file_1.png", "can_delete": False}],
            "count": 1,
        }
        assert mock_list.call_args.args == ("e-1", "facturador")

    def test_get_imagenes_default_scope_observacion(self):
        """Sin scope → observación (R4: callers de export no cambian)."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ) as mock_list,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value=None,
            ),
        ):
            result = get_imagenes("e-1")

        assert result["status"] == "success"
        assert mock_list.call_args.args == ("e-1", "")

    def test_upload_imagen_scope_passthrough(self):
        """upload_imagen(id, file, scope, username) pasa username a storage."""
        with (
            patch(
                "app.services.control_errores_service.obtener_error",
                return_value={"id": "e-1"},
            ),
            patch(
                "app.services.control_errores_service.guardar_imagen",
                return_value=(True, "file_1.png"),
            ) as mock_guardar,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
        ):
            result = upload_imagen("e-1", _png(), scope="facturador", username="u1")

        assert result["status"] == "success"
        assert result["data"]["filename"] == "file_1.png"
        args = mock_guardar.call_args.args
        assert args[0] == "e-1"
        assert args[2] == "facturador"
        assert mock_guardar.call_args.kwargs["username"] == "u1"

    def test_upload_imagen_sin_username_legacy(self):
        """upload_imagen sin username → guardar_imagen sin username (legacy)."""
        with (
            patch(
                "app.services.control_errores_service.obtener_error",
                return_value={"id": "e-1"},
            ),
            patch(
                "app.services.control_errores_service.guardar_imagen",
                return_value=(True, "file_1.png"),
            ) as mock_guardar,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
        ):
            result = upload_imagen("e-1", _png(), scope="facturador")

        assert result["status"] == "success"
        assert mock_guardar.call_args.kwargs.get("username") is None

    def test_delete_imagen_scope_passthrough(self):
        """delete_imagen(id, filename, scope) delega el scope a storage."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value="u1",
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                return_value=(True, ""),
            ) as mock_elim,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=0,
            ),
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="facturador", username="u1"
            )

        assert result["status"] == "success"
        assert mock_elim.call_args.args == ("e-1", "file_1.png", "facturador")

    def test_delete_imagen_no_listado_404(self):
        """R1/FA-6/R3: nombre no listado (o path trick) → envelope 404."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=[],
            ) as mock_list,
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                side_effect=AssertionError("no debe tocar storage"),
            ),
        ):
            result = delete_imagen(
                "e-1", "../file_1.png", scope="facturador", username="u1"
            )

        assert isinstance(result, tuple)
        assert result[1] == 404
        assert result[0]["status"] == "error"
        assert mock_list.call_args.args == ("e-1", "facturador")

    def test_delete_imagen_scope_invalido_400(self):
        """R2: scope fuera del allowlist → envelope 400 (ValueError backstop)."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                side_effect=ValueError("scope no permitido: 'bogus'"),
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
            ),
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="bogus", username="u1"
            )

        assert isinstance(result, tuple)
        assert result[1] == 400
        assert result[0]["status"] == "error"

    def test_upload_imagen_scope_invalido_400(self):
        """R2: guardar con scope inválido → envelope 400."""
        with (
            patch(
                "app.services.control_errores_service.obtener_error",
                return_value={"id": "e-1"},
            ),
            patch(
                "app.services.control_errores_service.guardar_imagen",
                side_effect=ValueError("scope no permitido: 'bogus'"),
            ),
        ):
            result = upload_imagen("e-1", _png(), scope="bogus")

        assert isinstance(result, tuple)
        assert result[1] == 400
        assert result[0]["status"] == "error"


# =============================================================================
# FA-8/FA-9: can_delete en GET y ownership en DELETE (tasks 2.1, 2.2)
# =============================================================================


class TestServiceOwnership:
    """FA-9: get_imagenes calcula can_delete por archivo (admin/dueño/ajeno)."""

    def test_get_imagenes_can_delete_dueño(self):
        """Dueño (obtener_uploader == username) → can_delete true."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png", "file_2.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=2,
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                side_effect=lambda eid, fname, scope="": (
                    "u1" if fname == "file_1.png" else None
                ),
            ),
        ):
            result = get_imagenes("e-1", scope="facturador", username="u1")

        assert result["data"]["imagenes"] == [
            {"filename": "file_1.png", "can_delete": True},
            {"filename": "file_2.png", "can_delete": False},
        ]

    def test_get_imagenes_can_delete_admin(self):
        """Admin (*) → can_delete true en todos (incl. legacy)."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value=None,
            ),
        ):
            result = get_imagenes("e-1", scope="facturador", username="admin", is_admin=True)

        assert result["data"]["imagenes"] == [
            {"filename": "file_1.png", "can_delete": True}
        ]

    def test_get_imagenes_can_delete_ajeno_legacy(self):
        """Ajeno o legacy (sin dueño) → can_delete false."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=1,
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value="otro",
            ),
        ):
            result = get_imagenes("e-1", scope="facturador", username="u1")

        assert result["data"]["imagenes"] == [
            {"filename": "file_1.png", "can_delete": False}
        ]

    # FA-8: delete_imagen → 403 si no admin y no dueño
    def test_delete_imagen_dueño_200(self):
        """Dueño borra su archivo → 200."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value="u1",
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                return_value=(True, ""),
            ),
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=0,
            ),
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="facturador", username="u1"
            )

        assert isinstance(result, tuple) is False
        assert result["status"] == "success"

    def test_delete_imagen_ajeno_403(self):
        """Usuario distinto del dueño → 403, storage no se toca."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value="otro",
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                side_effect=AssertionError("no debe tocar storage"),
            ) as mock_elim,
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="facturador", username="u1"
            )

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert result[0]["status"] == "error"
        assert "autor" in result[0]["errors"][0]
        mock_elim.assert_not_called()

    def test_delete_imagen_legacy_no_admin_403(self):
        """Legacy sin dueño, no-admin → 403."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value=None,
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                side_effect=AssertionError("no debe tocar storage"),
            ) as mock_elim,
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="facturador", username="u1"
            )

        assert isinstance(result, tuple)
        assert result[1] == 403
        mock_elim.assert_not_called()

    def test_delete_imagen_admin_200(self):
        """Admin (*) borra cualquiera (incl. legacy) → 200."""
        with (
            patch(
                "app.services.control_errores_service.listar_imagenes",
                return_value=["file_1.png"],
            ),
            patch(
                "app.services.control_errores_service.obtener_uploader",
                return_value=None,
            ),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                return_value=(True, ""),
            ) as mock_elim,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=0,
            ),
        ):
            result = delete_imagen(
                "e-1", "file_1.png", scope="facturador", username="admin", is_admin=True
            )

        assert result["status"] == "success"
        mock_elim.assert_called_once()


# =============================================================================
# Integration: rutas con ?scope= (tasks 1.4, 3.2, 3.3)
# =============================================================================


def _login(app_client, permisos, username="val1"):
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["rol"] = "validador"
        sess["username"] = username
        sess["permisos"] = permisos


class TestRoutesScope:
    """3.2/3.3/FA-4: POST/GET/DELETE/serve scoped vía app_client."""

    def test_post_scope_facturador_reader_200_persisted(self, app_client, tmp_imagenes):
        """FA-4: POST ?scope=facturador con lector (base) → 200 y persiste con dueño.

        El adjunto de facturador lo sube quien tenga ``control_urgencias``
        (con o sin ``:write``) o admin (FA-4, D15). El dueño registrado es el
        username de la sesión (FA-7).
        """
        _login(app_client, ["control_urgencias"], username="urgencias")
        with patch(
            "app.services.control_errores_service.obtener_error",
            return_value={"id": "e-1"},
        ):
            resp = app_client.post(
                "/api/control-errores/e-1/imagenes?scope=facturador",
                data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["filename"] == "file_1.png"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()
        # Observación (default scope) intacta
        assert not (tmp_imagenes / "e-1" / "file_1.png").exists()
        # FA-7: el sidecar facturador registra al subidor (username de sesión)
        import json
        sidecar = tmp_imagenes / "e-1" / "facturador" / ".owner.json"
        assert json.loads(sidecar.read_text()) == {"file_1.png": "urgencias"}

    def test_post_scope_facturador_write_200_persisted(self, app_client, tmp_imagenes):
        """FA-4: POST scoped facturador con :write → 200 y persiste (invertido).

        Antes :write quedaba BLOQUEADO de subir adjuntos de facturador (403);
        con la nueva matriz, ``:write`` también puede subir (D15).
        """
        _login(app_client, ["control_urgencias", "control_urgencias:write"], username="val1")
        with patch(
            "app.services.control_errores_service.obtener_error",
            return_value={"id": "e-1"},
        ):
            resp = app_client.post(
                "/api/control-errores/e-1/imagenes?scope=facturador",
                data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["filename"] == "file_1.png"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_post_scope_observacion_reader_403_nothing_persisted(
        self, app_client, tmp_imagenes
    ):
        """FA-4: POST scope "" (observación) con lector → 403, nada se persiste.

        El scope de observación conserva su comportamiento: un lector base
        NO puede subir archivos de observación.
        """
        _login(app_client, ["control_urgencias"], username="urgencias")
        resp = app_client.post(
            "/api/control-errores/e-1/imagenes",
            data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert resp.get_json() == {"status": "error", "data": {}, "errors": ["Permiso denegado"]}
        assert not (tmp_imagenes / "e-1").exists()

    def test_post_scope_observacion_write_200_persisted(self, app_client, tmp_imagenes):
        """FA-4: POST scope "" (observación) con :write → 200 y persiste."""
        _login(app_client, ["control_urgencias", "control_urgencias:write"], username="val1")
        with patch(
            "app.services.control_errores_service.obtener_error",
            return_value={"id": "e-1"},
        ):
            resp = app_client.post(
                "/api/control-errores/e-1/imagenes",
                data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["filename"] == "file_1.png"
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()

    def test_post_scope_facturador_admin_200_persisted(self, app_client, tmp_imagenes):
        """FA-4: POST ?scope=facturador con admin (*) → 200 y persiste."""
        _login(app_client, ["*"], username="admin")
        with patch(
            "app.services.control_errores_service.obtener_error",
            return_value={"id": "e-1"},
        ):
            resp = app_client.post(
                "/api/control-errores/e-1/imagenes?scope=facturador",
                data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["filename"] == "file_1.png"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_post_scope_bogus_400(self, app_client, tmp_imagenes):
        """R2: POST ?scope=bogus → 400, nada se persiste."""
        _login(app_client, ["control_urgencias:write"])
        resp = app_client.post(
            "/api/control-errores/e-1/imagenes?scope=bogus",
            data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert not (tmp_imagenes / "e-1").exists()

    def test_responsable_facturacion_no_accede_flujo_imagenes(
        self, app_client, tmp_imagenes
    ):
        """FA-4: responsable_facturacion NO otorga acceso al flujo de imágenes.

        El rol no tiene permisos de control_urgencias: el decorador de ruta
        lo bloquea (302 a login, ya que la request no es XHR) y nada se
        persiste. El flujo de imágenes queda fuera de alcance de ese rol.
        """
        _login(app_client, ["responsable_facturacion"], username="resp")
        resp = app_client.post(
            "/api/control-errores/e-1/imagenes?scope=facturador",
            data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
            content_type="multipart/form-data",
        )
        # Bloqueado por auth (sin control_urgencias): redirige a login (302)
        assert resp.status_code == 302
        assert not (tmp_imagenes / "e-1").exists()

        # Tras el 302 el decorador cerró la sesión → el siguiente request es 401
        resp = app_client.delete(
            "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador"
        )
        assert resp.status_code in (302, 401)  # bloqueado por auth
        assert not (tmp_imagenes / "e-1").exists()

    def test_get_imagenes_scope_facturador_aisla(self, app_client, tmp_imagenes):
        """M-1/FA-9: GET scoped lista objetos {filename, can_delete}; default obs."""
        errores_storage.guardar_imagen("e-1", _png())  # → {id}/file_1.png
        errores_storage.guardar_imagen(
            "e-1", _FakeFile("fac.jpg"), scope="facturador"
        )  # → {id}/facturador/file_1.jpg
        _login(app_client, ["control_urgencias", "control_urgencias:write"], username="val1")

        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp_fac = app_client.get("/api/control-errores/e-1/imagenes?scope=facturador")
            assert resp_fac.status_code == 200
            assert resp_fac.get_json()["data"]["imagenes"] == [
                {"filename": "file_1.jpg", "can_delete": False}
            ]
            assert resp_fac.get_json()["data"]["count"] == 1

            resp_obs = app_client.get("/api/control-errores/e-1/imagenes")
            assert resp_obs.status_code == 200
            assert resp_obs.get_json()["data"]["imagenes"] == [
                {"filename": "file_1.png", "can_delete": False}
            ]

    def test_get_imagenes_scope_bogus_400(self, app_client):
        """R2: GET ?scope=bogus → 400."""
        _login(app_client, ["control_urgencias", "control_urgencias:write"])
        resp = app_client.get("/api/control-errores/e-1/imagenes?scope=bogus")
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    def test_serve_scope_facturador_200(self, app_client, tmp_imagenes):
        """FA-6: GET scoped de archivo listado → 200 con el archivo."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        resp = app_client.get(
            "/api/control-errores/e-1/imagenes/file_1.png?scope=facturador"
        )
        assert resp.status_code == 200
        assert resp.data == b"\x89PNG\r\n\x1a\nfake-png"

    def test_serve_scope_facturador_no_listado_404(self, app_client, tmp_imagenes):
        """FA-6: GET scoped de nombre no listado → 404, nada servido."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        resp = app_client.get(
            "/api/control-errores/e-1/imagenes/otro.png?scope=facturador"
        )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"

    def test_serve_scope_facturador_path_trick_404(self, app_client, tmp_imagenes):
        """FA-6: GET scoped '../file_1.png' → 404, nada servido."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        resp = app_client.get(
            "/api/control-errores/e-1/imagenes/../file_1.png?scope=facturador"
        )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"

    def test_serve_default_scope_observacion_200(self, app_client, tmp_imagenes):
        """Export links (sin scope) siguen sirviendo observación (R4)."""
        errores_storage.guardar_imagen("e-1", _png())
        resp = app_client.get("/api/control-errores/e-1/imagenes/file_1.png")
        assert resp.status_code == 200
        assert resp.data == b"\x89PNG\r\n\x1a\nfake-png"

    def test_serve_sidecar_owner_json_404(self, app_client, tmp_imagenes):
        """R3: GET scoped del sidecar .owner.json → 404 (no servible)."""
        errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="u"
        )
        assert (tmp_imagenes / "e-1" / "facturador" / ".owner.json").is_file()
        resp = app_client.get(
            "/api/control-errores/e-1/imagenes/.owner.json?scope=facturador"
        )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"

    def test_serve_sidecar_owner_json_default_404(self, app_client, tmp_imagenes):
        """R3: GET default scope del sidecar → 404."""
        errores_storage.guardar_imagen("e-1", _png(), username="u")
        resp = app_client.get("/api/control-errores/e-1/imagenes/.owner.json")
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"

    def test_delete_scope_facturador_path_trick_404_file_intact(
        self, app_client, tmp_imagenes
    ):
        """R1: DELETE scoped '../file_1.png' → 404; ambos scopes intactos.

        Se usa un LECTOR (base sin :write): el path trick llega a la
        validación R1 de storage (no al 403 de permiso de facturador).
        """
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen("e-1", _png())  # observación
        _login(app_client, ["control_urgencias"], username="urgencias")
        resp = app_client.delete(
            "/api/control-errores/e-1/imagenes/?filename=../file_1.png&scope=facturador"
        )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()

    def test_delete_scope_facturador_owner_200(self, app_client, tmp_imagenes):
        """FA-8: dueño borra su archivo facturador → 200 y queda borrado."""
        errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="urgencias"
        )
        _login(app_client, ["control_urgencias"], username="urgencias")
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador"
            )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"
        assert resp.get_json()["data"]["count"] == 0
        assert not (tmp_imagenes / "e-1" / "facturador" / "file_1.png").exists()

    def test_delete_scope_facturador_ajeno_403_nothing_deleted(
        self, app_client, tmp_imagenes
    ):
        """FA-8: DELETE ajeno (no dueño, no admin) → 403, nada se borra."""
        errores_storage.guardar_imagen(
            "e-1", _png(), scope="facturador", username="otro"
        )
        _login(app_client, ["control_urgencias", "control_urgencias:write"], username="val1")
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_delete_scope_facturador_legacy_no_admin_403(self, app_client, tmp_imagenes):
        """FA-8: legacy sin dueño + no-admin → 403, nada se borra."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")  # sin username
        _login(app_client, ["control_urgencias"], username="urgencias")
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()

    def test_delete_scope_observacion_reader_403_nothing_deleted(
        self, app_client, tmp_imagenes
    ):
        """DELETE scope "" (observación) con lector → 403, nada se borra."""
        errores_storage.guardar_imagen("e-1", _png())
        _login(app_client, ["control_urgencias"], username="urgencias")
        resp = app_client.delete(
            "/api/control-errores/e-1/imagenes/?filename=file_1.png",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()

    def test_delete_scope_observacion_owner_200(self, app_client, tmp_imagenes):
        """FA-8: dueño (:write) borra su archivo de observación → 200."""
        errores_storage.guardar_imagen("e-1", _png(), username="val1")
        _login(app_client, ["control_urgencias", "control_urgencias:write"], username="val1")
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png"
            )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"
        assert not (tmp_imagenes / "e-1" / "file_1.png").exists()

    def test_delete_scope_facturador_admin_200(self, app_client, tmp_imagenes):
        """FA-8: admin (*) borra legacy (sin dueño) → 200."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")  # sin dueño
        _login(app_client, ["*"], username="admin")
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador"
            )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"
        assert not (tmp_imagenes / "e-1" / "facturador" / "file_1.png").exists()


# =============================================================================
# Review fix: LIST/DELETE con UUID válido pero sin registro → 404 antes de FS
# =============================================================================


class TestRecordExistenceGuard:
    """UUID sintácticamente válido pero sin registro → 404 en listado y borrado.

    La ruta consulta el store vía ``obtener_error`` ANTES de cualquier
    resolución de filesystem; un UUID inexistente no toca storage de imágenes.
    """

    UUID_SIN_REGISTRO = "00000000-0000-0000-0000-000000000000"

    def test_list_imagenes_uuid_sin_registro_404(self, app_client, tmp_imagenes):
        """GET imágenes de UUID válido inexistente → 404 sin tocar storage."""
        _login(app_client, ["control_urgencias", "control_urgencias:write"])
        with (
            patch("app.routes.control_errores.obtener_error", return_value=None),
            patch(
                "app.services.control_errores_service.listar_imagenes",
                side_effect=AssertionError("no debe resolver el filesystem"),
            ),
        ):
            resp = app_client.get(
                f"/api/control-errores/{self.UUID_SIN_REGISTRO}/imagenes"
            )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"

    def test_delete_imagen_uuid_sin_registro_404(self, app_client, tmp_imagenes):
        """DELETE imagen de UUID válido inexistente → 404 sin tocar storage."""
        _login(app_client, ["control_urgencias:write"])
        with (
            patch("app.routes.control_errores.obtener_error", return_value=None),
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                side_effect=AssertionError("no debe resolver el filesystem"),
            ),
        ):
            resp = app_client.delete(
                f"/api/control-errores/{self.UUID_SIN_REGISTRO}/imagenes/?filename=file_1.png"
            )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"
