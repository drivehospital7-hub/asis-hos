"""Tests para `ultima_modificacion_estado` en app/utils/errores_storage.py.

Solo backend, no visible: se actualiza únicamente cuando cambia `estado`.
"""

from __future__ import annotations

from unittest.mock import patch

from app.utils.errores_storage import (
    actualizar_error,
    backfill_ultima_modificacion_estado,
    crear_error,
    obtener_novedades,
)


def _store(error: dict | None = None) -> dict:
    return {"errores": [error] if error else []}


class TestUltimaModificacionEstado:
    def test_crear_inicializa_campo(self) -> None:
        with (
            patch("app.utils.errores_storage._leer_datos", return_value=_store()),
            patch("app.utils.errores_storage._escribir_datos"),
        ):
            nuevo = crear_error("Otros", "FEV1", "obs", "S", "RESP")
        assert nuevo["ultima_modificacion_estado"]

    def test_solo_cambia_con_estado_distinto(self) -> None:
        base = {
            "id": "e1",
            "estado": "S",
            "ultima_modificacion_estado": "2026-01-01T10:00:00",
        }
        with (
            patch("app.utils.errores_storage._leer_datos", return_value=_store(dict(base))),
            patch("app.utils.errores_storage._escribir_datos"),
        ):
            mismo = actualizar_error("e1", observacion="otra")
            assert mismo is not None
            assert mismo["ultima_modificacion_estado"] == "2026-01-01T10:00:00"

            igual = actualizar_error("e1", estado="S")
            assert igual is not None
            assert igual["ultima_modificacion_estado"] == "2026-01-01T10:00:00"

            cambio = actualizar_error("e1", estado="R")
            assert cambio is not None
            assert cambio["estado"] == "R"
            assert cambio["ultima_modificacion_estado"] != "2026-01-01T10:00:00"

    def test_backfill_copia_actualizado_en(self) -> None:
        base = {
            "id": "e1",
            "estado": "S",
            "creado_en": "2026-01-01T10:00:00",
            "actualizado_en": "2026-02-02T11:00:00",
        }
        con_campo = dict(base, id="e2", ultima_modificacion_estado="2026-03-03T12:00:00")
        with (
            patch(
                "app.utils.errores_storage._leer_datos",
                return_value={"errores": [dict(base), con_campo]},
            ),
            patch("app.utils.errores_storage._escribir_datos") as mock_write,
        ):
            touched = backfill_ultima_modificacion_estado()
        assert touched == 1
        saved = mock_write.call_args[0][0]["errores"]
        assert saved[0]["ultima_modificacion_estado"] == "2026-02-02T11:00:00"
        assert saved[1]["ultima_modificacion_estado"] == "2026-03-03T12:00:00"

    def test_backfill_idempotente(self) -> None:
        base = {
            "id": "e1",
            "estado": "S",
            "ultima_modificacion_estado": "2026-03-03T12:00:00",
        }
        with (
            patch(
                "app.utils.errores_storage._leer_datos",
                return_value={"errores": [base]},
            ),
            patch("app.utils.errores_storage._escribir_datos") as mock_write,
        ):
            assert backfill_ultima_modificacion_estado() == 0
            mock_write.assert_not_called()


class TestObtenerNovedades:
    def test_retorna_registros_crudos_sin_conteos(self) -> None:
        errores = [
            {"id": "e1", "factura": "FEV1", "estado": "S"},
            {"id": "e2", "factura": "FEV2", "estado": "R"},
        ]
        with patch(
            "app.utils.errores_storage._leer_datos",
            return_value={"errores": errores},
        ):
            novedades = obtener_novedades()
        assert novedades == errores
        assert all("imagenes_count" not in n for n in novedades)

    def test_sin_archivo_lista_vacia(self) -> None:
        with patch(
            "app.utils.errores_storage._leer_datos",
            return_value={"errores": [], "ultima_actualizacion": None},
        ):
            assert obtener_novedades() == []


class TestSnapshotMtime:
    def test_save_snapshot_persiste_mtime(
        self, tmp_path, monkeypatch
    ) -> None:
        """Round-trip: mtime del scan sobrevive al snapshot en disco."""
        import json

        import app.services.monitoreo_carpetas.watcher as watcher_mod
        from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult

        snapshot_file = tmp_path / "monitoreo_snapshot.json"
        monkeypatch.setattr(watcher_mod, "_SNAPSHOT_FILE", snapshot_file)
        monkeypatch.setattr(
            watcher_mod, "_SNAPSHOT_DIR", tmp_path, raising=False
        )

        watcher = watcher_mod.FolderWatcher.__new__(watcher_mod.FolderWatcher)
        import threading

        watcher._lock = threading.Lock()
        watcher._roots = ["//fake-root"]
        watcher._excel_stale = False
        watcher._excel_generated_at = None
        watcher._last_reconcile_at = None
        watcher._last_scan_at = None
        watcher._result = ScanResult(
            facturas=[
                InvoiceRecord(
                    filename="FEV123",
                    facturador="Fact1",
                    full_path="//fake-root/Fact1/FEV123",
                    status="En revisión",
                    invoice_type="FEV",
                    invoice_code="FEV123",
                    mtime=1_700_000_000.0,
                )
            ],
        )

        watcher._save_snapshot()

        data = json.loads(snapshot_file.read_text(encoding="utf-8"))
        assert data["result"]["facturas"][0]["mtime"] == 1_700_000_000.0

    def test_snapshot_viejo_sin_mtime_no_rompe_load(
        self, tmp_path, monkeypatch
    ) -> None:
        """Snapshot viejo (facturas sin mtime) se lee sin errores."""
        import json

        import app.services.monitoreo_carpetas.watcher as watcher_mod

        snapshot_file = tmp_path / "monitoreo_snapshot.json"
        snapshot_file.write_text(
            json.dumps({
                "roots": ["//fake-root"],
                "result": {
                    "facturas": [
                        {
                            "filename": "FEV123",
                            "facturador": "Fact1",
                            "full_path": "//fake-root/Fact1/FEV123",
                            "status": "En revisión",
                            "invoice_type": "FEV",
                            "invoice_code": "FEV123",
                        }
                    ],
                },
            }),
            encoding="utf-8",
        )
        monkeypatch.setattr(watcher_mod, "_SNAPSHOT_FILE", snapshot_file)

        watcher = watcher_mod.FolderWatcher.__new__(watcher_mod.FolderWatcher)
        import threading

        watcher._lock = threading.Lock()
        watcher._result = None
        watcher._roots = []
        watcher._excel_stale = False
        watcher._excel_generated_at = None
        watcher._last_reconcile_at = None
        watcher._last_scan_at = None
        watcher._load_snapshot()  # no debe lanzar; datos viejos se descartan
        assert watcher._roots == ["//fake-root"]
        assert watcher._result is None
