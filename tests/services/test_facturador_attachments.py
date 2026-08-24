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
            ) as mock_count,
        ):
            result = get_imagenes("e-1", scope="facturador")

        assert result["status"] == "success"
        assert result["data"] == {"imagenes": ["file_1.png"], "count": 1}
        assert mock_list.call_args.args == ("e-1", "facturador")
        assert mock_count.call_args.args == ("e-1", "facturador")

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
            ) as mock_count,
        ):
            result = get_imagenes("e-1")

        assert result["status"] == "success"
        assert mock_list.call_args.args == ("e-1", "")
        assert mock_count.call_args.args == ("e-1", "")

    def test_upload_imagen_scope_passthrough(self):
        """upload_imagen(id, file, scope) guarda y cuenta en ese scope."""
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
        assert result["data"]["filename"] == "file_1.png"
        args = mock_guardar.call_args.args
        assert args[0] == "e-1"
        assert args[2] == "facturador"

    def test_delete_imagen_scope_passthrough(self):
        """delete_imagen(id, filename, scope) delega el scope a storage."""
        with (
            patch(
                "app.services.control_errores_service.eliminar_imagen",
                return_value=(True, ""),
            ) as mock_elim,
            patch(
                "app.services.control_errores_service.obtener_imagenes_count",
                return_value=0,
            ),
        ):
            result = delete_imagen("e-1", "file_1.png", scope="facturador")

        assert result["status"] == "success"
        assert mock_elim.call_args.args == ("e-1", "file_1.png", "facturador")

    def test_delete_imagen_no_listado_404(self):
        """R1/FA-6: nombre no listado (o path trick) → envelope 404."""
        with patch(
            "app.services.control_errores_service.eliminar_imagen",
            return_value=(False, "Imagen no encontrada"),
        ) as mock_elim:
            result = delete_imagen("e-1", "../file_1.png", scope="facturador")

        assert isinstance(result, tuple)
        assert result[1] == 404
        assert result[0]["status"] == "error"
        assert mock_elim.call_args.args == ("e-1", "../file_1.png", "facturador")

    def test_delete_imagen_scope_invalido_400(self):
        """R2: scope fuera del allowlist → envelope 400 (ValueError backstop)."""
        with patch(
            "app.services.control_errores_service.eliminar_imagen",
            side_effect=ValueError("scope no permitido: 'bogus'"),
        ):
            result = delete_imagen("e-1", "file_1.png", scope="bogus")

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

    def test_post_scope_facturador_write_200_persisted(self, app_client, tmp_imagenes):
        """FA-4: POST ?scope=facturador con :write → 200 y persiste en {id}/facturador/."""
        _login(app_client, ["control_urgencias", "control_urgencias:write"])
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

    def test_post_scope_facturador_read_only_403_nothing_persisted(
        self, app_client, tmp_imagenes
    ):
        """FA-4: POST scoped sin :write → 403, nada se persiste."""
        _login(app_client, ["control_urgencias"], username="urgencias")
        resp = app_client.post(
            "/api/control-errores/e-1/imagenes?scope=facturador",
            data={"imagen": (BytesIO(b"\x89PNG\r\n\x1a\nfake"), "captura.png")},
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert not (tmp_imagenes / "e-1").exists()

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

    def test_get_imagenes_scope_facturador_aisla(self, app_client, tmp_imagenes):
        """M-1: GET scoped lista solo facturador/; GET default solo observación."""
        errores_storage.guardar_imagen("e-1", _png())  # → {id}/file_1.png
        errores_storage.guardar_imagen(
            "e-1", _FakeFile("fac.jpg"), scope="facturador"
        )  # → {id}/facturador/file_1.jpg
        _login(app_client, ["control_urgencias", "control_urgencias:write"])

        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp_fac = app_client.get("/api/control-errores/e-1/imagenes?scope=facturador")
            assert resp_fac.status_code == 200
            assert resp_fac.get_json()["data"]["imagenes"] == ["file_1.jpg"]
            assert resp_fac.get_json()["data"]["count"] == 1

            resp_obs = app_client.get("/api/control-errores/e-1/imagenes")
            assert resp_obs.status_code == 200
            assert resp_obs.get_json()["data"]["imagenes"] == ["file_1.png"]

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

    def test_delete_scope_facturador_path_trick_404_file_intact(
        self, app_client, tmp_imagenes
    ):
        """R1: DELETE scoped '../file_1.png' → 404; ambos scopes intactos."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        errores_storage.guardar_imagen("e-1", _png())  # observación
        _login(app_client, ["control_urgencias:write"])
        resp = app_client.delete(
            "/api/control-errores/e-1/imagenes/?filename=../file_1.png&scope=facturador"
        )
        assert resp.status_code == 404
        assert resp.get_json()["status"] == "error"
        assert (tmp_imagenes / "e-1" / "facturador" / "file_1.png").is_file()
        assert (tmp_imagenes / "e-1" / "file_1.png").is_file()

    def test_delete_scope_facturador_listed_200(self, app_client, tmp_imagenes):
        """DELETE scoped de archivo listado → 200 y queda borrado."""
        errores_storage.guardar_imagen("e-1", _png(), scope="facturador")
        _login(app_client, ["control_urgencias:write"])
        with patch("app.routes.control_errores.obtener_error", return_value={"id": "e-1"}):
            resp = app_client.delete(
                "/api/control-errores/e-1/imagenes/?filename=file_1.png&scope=facturador"
            )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"
        assert resp.get_json()["data"]["count"] == 0
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
