"""Edad detalle largo: edad_anios_meses y edad_meses_dias.

Claves nuevas planas (sin punto) con formato largo y unidades. No tocan
date.edad ni date.edad_meses. Opt-in: solo se calculan cuando la regla
las referencia en detalle_a/b o descripcion_template.
"""

from __future__ import annotations

from types import SimpleNamespace


def test_format_anios_meses():
    from app.services.engine.providers import format_anios_meses
    assert format_anios_meses("2018-01-15", "2025-06-20") == "7 años 5 meses"


def test_format_meses_dias():
    from app.services.engine.providers import format_meses_dias
    assert format_meses_dias("2018-01-15", "2025-06-27") == "89 meses 12 días"


def test_format_invalidas_dan_vacio():
    from app.services.engine.providers import format_anios_meses, format_meses_dias
    assert format_anios_meses("not-a-date", "garbage") == ""
    assert format_meses_dias("not-a-date", "garbage") == ""
    assert format_anios_meses(None, "2025-06-20") == ""
    assert format_meses_dias("2018-01-15", None) == ""


def test_format_factura_menor_da_vacio():
    from app.services.engine.providers import format_anios_meses, format_meses_dias
    assert format_anios_meses("2025-06-20", "2018-01-15") == ""
    assert format_meses_dias("2025-06-20", "2018-01-15") == ""


def _row_rule(**over):
    base = {
        "detalle_a_campo": None,
        "detalle_b_campo": None,
        "descripcion_template": None,
    }
    base.update(over)
    return SimpleNamespace(**base)


def test_engine_row_path_enriquece_solo_lo_pedido():
    from app.services.engine.engine import _enrich_edad_detalle
    problem = {
        "factura": "F1",
        "fec_nacimiento": "2018-01-15",
        "fec_factura": "2025-06-20",
    }
    rule = _row_rule(detalle_a_campo="Edad: {edad_anios_meses}")
    _enrich_edad_detalle(problem, {}, {}, rule=rule)
    assert problem["edad_anios_meses"] == "7 años 5 meses"
    assert "edad_meses_dias" not in problem


def test_engine_row_path_no_setea_cuando_no_lo_pide():
    from app.services.engine.engine import _enrich_edad_detalle
    problem = {
        "factura": "F1",
        "fec_nacimiento": "2018-01-15",
        "fec_factura": "2025-06-20",
    }
    rule = _row_rule(detalle_a_campo="codigo")
    _enrich_edad_detalle(problem, {}, {}, rule=rule)
    assert "edad_anios_meses" not in problem
    assert "edad_meses_dias" not in problem


def _group_rule_info(**over):
    base = {
        "id": 1, "version": 1, "dominio": "odontologia",
        "nombre": "edad_detalle", "descripcion": "Edad detalle",
        "severidad": "error",
    }
    base.update(over)
    return base


def _eval_group(rule_info, fec_nac="2018-01-15", fec_fact="2025-06-27"):
    from app.services.engine.condition_evaluator import ConditionEvaluator
    from app.services.engine.evidence_collector import EvidenceCollector
    from app.services.engine.group_evaluator import GroupEvaluator
    ce = ConditionEvaluator()
    tree = ce.build_tree([
        {"id": 1, "padre_id": None, "tipo": "atomic", "operador": "eq",
         "fuente_datos": "invoice.codigo", "valor_esperado": "X", "orden": 0},
    ])
    groups = {"F1": [2]}
    rows = [{
        "numero_factura": "F1", "codigo": "X",
        "fec_nacimiento": fec_nac, "fec_factura": fec_fact,
    }]
    return GroupEvaluator.evaluate(
        groups, None, {}, [], tree, ce, rule_info,
        EvidenceCollector(), record_evidence=False, rows=rows,
    )


def test_group_evaluate_enriquece_solo_lo_pedido():
    results = _eval_group(_group_rule_info(
        detalle_a_campo="Edad: {edad_meses_dias}",
    ))
    assert len(results) == 1
    assert results[0]["edad_meses_dias"] == "89 meses 12 días"
    assert "edad_anios_meses" not in results[0]


def test_group_evaluate_no_setea_cuando_no_lo_pide():
    results = _eval_group(_group_rule_info(detalle_a_campo="codigo"))
    assert len(results) == 1
    assert "edad_anios_meses" not in results[0]
    assert "edad_meses_dias" not in results[0]


def test_group_evaluate_sin_fechas_no_setea():
    results = _eval_group(
        _group_rule_info(detalle_a_campo="{edad_anios_meses}"),
        fec_nac="not-a-date", fec_fact="garbage",
    )
    assert len(results) == 1
    assert "edad_anios_meses" not in results[0]
