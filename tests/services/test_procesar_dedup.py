"""Tests para app/services/procesar_dedup.py (dedup display-only de /procesar).

Cubre: mismo grupo/misma factura (gana menor prioridad), distintos grupos,
distintas facturas, empates (severidad -> regla id -> primer match) y legacy
sin regla. Herméticos: meta inyectada, sin DB (salvo el test best-effort que
fuerza el fallo de sesión y verifica que no rompe).
"""

from __future__ import annotations

import pytest

from app.services.procesar_dedup import (
    DEFAULT_PRIORIDAD,
    _parse_regla_id,
    dedup_procesar_items,
)


def _item(factura, grupo, regla="", tipo_factura="Urgencias",
          severidad="", descripcion=""):
    """Fila como las que arma /procesar en all_items."""
    return {
        "tipo_error": grupo,
        "tipo_factura": tipo_factura,
        "factura": factura,
        "fec_factura": "",
        "responsable_cierra": "",
        "descripcion": descripcion or f"{grupo} {regla}",
        "procedimiento": "",
        "detalle": "",
        "fecha_cierre_vacia": False,
        "regla": regla,
        **({"severidad": severidad} if severidad else {}),
    }


def _meta(mapping):
    """Helper: {regla_id: meta} desde {id: (prioridad, severidad)}."""
    return {
        rid: {"prioridad": prio, "severidad": sev}
        for rid, (prio, sev) in mapping.items()
    }


def test_mismo_grupo_misma_factura_gana_menor_prioridad():
    items = [
        _item("F1", "Centros de Costo", "#30"),
        _item("F1", "Centros de Costo", "#5"),
    ]
    meta = _meta({30: (30, "error"), 5: (5, "error")})
    result = dedup_procesar_items(items, regla_meta=meta)
    assert len(result) == 1
    assert result[0]["regla"] == "#5"
    assert result[0]["tipo_factura"] == "Urgencias"


def test_misma_factura_distintos_grupos_se_muestran_ambos():
    items = [
        _item("F1", "Centros de Costo", "#5"),
        _item("F1", "IDE Contrato", "#30"),
    ]
    meta = _meta({5: (5, "error"), 30: (30, "error")})
    result = dedup_procesar_items(items, regla_meta=meta)
    assert len(result) == 2
    assert {r["tipo_error"] for r in result} == {"Centros de Costo", "IDE Contrato"}


def test_distintas_facturas_mismo_grupo_se_muestran_ambas():
    items = [
        _item("F1", "Centros de Costo", "#5"),
        _item("F2", "Centros de Costo", "#30"),
    ]
    meta = _meta({5: (5, "error"), 30: (30, "error")})
    result = dedup_procesar_items(items, regla_meta=meta)
    assert len(result) == 2
    assert {r["factura"] for r in result} == {"F1", "F2"}


def test_empate_prioridad_desempata_severidad():
    items = [
        _item("F1", "G", "#7", severidad="warning"),
        _item("F1", "G", "#3", severidad="error"),
    ]
    meta = _meta({7: (10, "warning"), 3: (10, "error")})
    result = dedup_procesar_items(items, regla_meta=meta)
    assert len(result) == 1
    assert result[0]["regla"] == "#3"


def test_empate_total_desempata_menor_regla_id_y_primer_match():
    meta = _meta({7: (10, "error"), 3: (10, "error")})
    result = dedup_procesar_items(
        [_item("F1", "G", "#7"), _item("F1", "G", "#3")], regla_meta=meta
    )
    assert [r["regla"] for r in result] == ["#3"]

    # Ids iguales (o ausentes): gana el primer match, nunca se muestran todos.
    result = dedup_procesar_items(
        [_item("F1", "G", "#7", descripcion="primero"),
         _item("F1", "G", "#7", descripcion="segundo")],
        regla_meta=meta,
    )
    assert len(result) == 1
    assert result[0]["descripcion"] == "primero"


def test_sin_regla_no_rompe_y_usa_default():
    assert DEFAULT_PRIORIDAD == 100
    items = [
        _item("F1", "G", ""),
        _item("F1", "G", "", descripcion="legacy 2"),
    ]
    result = dedup_procesar_items(items, regla_meta={})
    assert len(result) == 1  # primer match, sin romper

    items = [_item("F1", "G1", ""), _item("F1", "G2", "")]
    assert len(dedup_procesar_items(items, regla_meta={})) == 2


def test_sin_db_best_effort_no_rompe(monkeypatch):
    def _boom():
        raise RuntimeError("DB down")

    monkeypatch.setattr("app.database.get_session", _boom)
    items = [_item("F1", "G", "#5"), _item("F1", "G", "#30")]
    result = dedup_procesar_items(items)  # regla_meta=None -> query que falla
    assert len(result) == 1  # empate en default -> menor id #5
    assert result[0]["regla"] == "#5"


@pytest.mark.parametrize(("raw", "expected"), [
    ("#60", 60),
    ("  #7  ", 7),
    ("", None),
    (None, None),
    ("abc", None),
    ("#", None),
])
def test_parse_regla_id(raw, expected):
    assert _parse_regla_id(raw) == expected
