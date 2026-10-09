"""Migración de categorías heredadas de control-novedades a Error/Notificación."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.utils import errores_storage
from scripts import migrar_categorias_novedades as migracion

LEGACY = [
    ("a", "Otros"),
    ("b", "Soportes de Carpeta"),
    ("c", "Factura Abierta"),
    ("d", "Carpeta no entregada"),
    ("e", "Factura"),
    ("f", "FURIPS"),
    ("g", "Factura Abierta"),
]


def _registro(error_id: str, tipo: str) -> dict:
    return {
        "id": error_id,
        "tipo_error": tipo,
        "factura": f"FEV-{error_id}",
        "observacion": "OBS",
        "estado": "S",
        "responsable": "LORENY ESPAÑA",
        "creado_en": "2026-08-10T10:00:00.000001",
        "actualizado_en": "2026-08-11T10:00:00.000001",
    }


@pytest.fixture()
def almacen(tmp_path):
    archivo = tmp_path / "control_errores.json"
    archivo.write_text(
        json.dumps(
            {"errores": [_registro(i, t) for i, t in LEGACY], "ultima_actualizacion": None},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with (
        patch.object(errores_storage, "DATA_DIR", tmp_path),
        patch.object(errores_storage, "ERRORES_FILE", archivo),
    ):
        yield archivo


def _leer(archivo) -> list[dict]:
    return json.loads(archivo.read_text(encoding="utf-8"))["errores"]


class TestMigrarCategorias:
    def test_simulacion_no_escribe_ni_respalda(self, almacen):
        original = almacen.read_bytes()

        resultado = migracion.migrar(aplicar=False)

        assert resultado["cambiados"] == 7
        assert resultado["respaldo"] is None
        assert almacen.read_bytes() == original
        assert list(almacen.parent.glob("*.bak-*")) == []

    def test_aplicar_mapea_todas_las_categorias(self, almacen):
        resultado = migracion.migrar(aplicar=True)

        tipos = {e["id"]: e["tipo_error"] for e in _leer(almacen)}
        assert tipos == {
            "a": "Error",
            "b": "Error",
            "c": "Notificación",
            "d": "Error",
            "e": "Error",
            "f": "Error",
            "g": "Notificación",
        }
        assert resultado["total"] == 7
        assert resultado["despues"] == {"Error": 5, "Notificación": 2}

    def test_aplicar_solo_cambia_tipo_error(self, almacen):
        antes = {e["id"]: e for e in _leer(almacen)}

        migracion.migrar(aplicar=True)

        for error in _leer(almacen):
            esperado = dict(antes[error["id"]], tipo_error=error["tipo_error"])
            assert error == esperado

    def test_aplicar_deja_respaldo_con_el_contenido_original(self, almacen):
        original = almacen.read_bytes()

        resultado = migracion.migrar(aplicar=True)

        respaldos = list(almacen.parent.glob("control_errores.json.bak-*"))
        assert len(respaldos) == 1
        assert str(respaldos[0]) == resultado["respaldo"]
        assert respaldos[0].read_bytes() == original

    def test_idempotente(self, almacen):
        migracion.migrar(aplicar=True)
        contenido = almacen.read_bytes()

        resultado = migracion.migrar(aplicar=True)

        assert resultado["cambiados"] == 0
        assert resultado["respaldo"] is None
        assert almacen.read_bytes() == contenido
        assert len(list(almacen.parent.glob("*.bak-*"))) == 1

    def test_json_invalido_aborta_sin_escribir(self, almacen):
        almacen.write_text("{no es json", encoding="utf-8")

        with pytest.raises(ValueError):
            migracion.migrar(aplicar=True)

        assert almacen.read_text(encoding="utf-8") == "{no es json"
        assert list(almacen.parent.glob("*.bak-*")) == []
