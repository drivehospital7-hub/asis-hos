"""Probe: engine propagates codigo_profesional into problem dicts.

The procesar detalle pipeline resolves templates like
"{codigo_profesional} {profesional_atiende}" via
``app.services.normalized_rows._resolve_detalle`` against the problem
dict — so the engine must copy ``codigo_profesional`` (and the
``detalle_b_campo`` template itself) onto every MATCH problem.
"""
from __future__ import annotations

from unittest.mock import MagicMock

RULE_NAME = "probe_codigo_profesional"
DOMINIO = "urgencias"
DESCRIPCION = "probe"
DETALLE_B = "{codigo_profesional} {profesional_atiende}"

_ROW_BASE = {
    "numero_factura": "F-1",
    "tipo_factura_descripcion": "Urgencias",
    "codigo": "890201",
    "profesional_atiende": "FULANA",
    "procedimiento": "PROC",
}


def _tree() -> list[dict]:
    return [
        {"id": 1, "padre_id": None, "tipo": "composite",
         "operador": "AND", "orden": 0},
        {"id": 2, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.tipo_factura_descripcion",
         "valor_esperado": "Urgencias", "orden": 0},
        {"id": 3, "padre_id": 1, "tipo": "atomic",
         "operador": "eq", "fuente_datos": "invoice.codigo_profesional",
         "valor_esperado": "03568", "orden": 1},
    ]


def _mock_session():
    from app.models import Regla

    session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query

    regla = Regla(
        id=1, nombre=RULE_NAME, dominio=DOMINIO,
        estado="active", version=1, prioridad=40, severidad="error",
        descripcion=DESCRIPCION,
    )
    regla.detalle_b_campo = DETALLE_B
    regla.detalle_a_campo = None
    regla.grupo_error = "Profesionales"
    mock_query.first.return_value = regla

    cond_mocks = []
    for cd in _tree():
        m = MagicMock()
        m.id = cd["id"]
        m.regla_id = 1
        m.padre_id = cd["padre_id"]
        m.tipo = cd["tipo"]
        m.operador = cd.get("operador")
        m.fuente_datos = cd.get("fuente_datos")
        m.valor_esperado = cd.get("valor_esperado")
        m.orden = cd.get("orden", 0)
        cond_mocks.append(m)
    mock_query.all.return_value = cond_mocks
    session.query.return_value = mock_query
    return session


def _run(rows: list[dict]):
    from app.services.engine.rule_based_detector import RuleBasedDetector

    session = _mock_session()
    return RuleBasedDetector(RULE_NAME, session, dominio=DOMINIO).detect(
        rows=rows, indices={}, persist=False,
    )


def test_match_propagates_codigo_profesional_and_detalle_template():
    res = _run([{**_ROW_BASE, "codigo_profesional": "03568"}])
    assert len(res) == 1
    problem = res[0]
    assert problem["codigo_profesional"] == "03568"
    assert problem["detalle_b_campo"] == DETALLE_B


def test_detalle_template_resolves_against_problem():
    from app.services.normalized_rows import _resolve_detalle

    res = _run([{**_ROW_BASE, "codigo_profesional": "03568"}])
    assert len(res) == 1
    assert _resolve_detalle(res[0], res[0]["detalle_b_campo"]) == "03568 FULANA"


def test_negative_codigo_profesional_no_match():
    res = _run([{**_ROW_BASE, "codigo_profesional": "01293"}])
    assert res == []
