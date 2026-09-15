"""Inferencia group_by bare: {"group_by": "numero_factura"} sin repetir la regla.

Contrato: al entrar en modo grupo, si el param solo trae group_by
(sin aggregations/filter), el engine infiere desde el arbol de condiciones:
- date.horas -> compute_horas(fec_factura, fecha_cierre -> estancia_horas)
- invoice.codigo con ops de set/membresia -> collect_set(codigo -> collect_set_codigo)
- atomic invoice.<campo factura-nivel> eq <literal> -> prefiltro pre-grupo
Si el param trae aggregations/filter explicitos, esos mandan (#60, #1, #2).

Caso testigo #44: 7h sin sala -> 1 MATCH; con sala o 3h -> NO MATCH.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

SALA_CODES = ["5DSB01", "05DSB01", "129B02", "38114", "38915"]
BARE_PARAM = {"group_by": "numero_factura"}


def _conds_44() -> list[dict]:
    """Arbol #44: AND(gt(date.horas, 6), eq(tipo, Urgencias), NOT(in(codigo, SALA)))."""
    return [
        {"id": 1, "padre_id": None, "tipo": "composite", "operador": "AND",
         "fuente_datos": None, "valor_esperado": None, "orden": 0},
        {"id": 2, "padre_id": 1, "tipo": "atomic", "operador": "gt",
         "fuente_datos": "date.horas", "valor_esperado": 6, "orden": 0},
        {"id": 3, "padre_id": 1, "tipo": "atomic", "operador": "eq",
         "fuente_datos": "invoice.tipo_factura_descripcion",
         "valor_esperado": "Urgencias", "orden": 1},
        {"id": 4, "padre_id": 1, "tipo": "composite", "operador": "NOT",
         "fuente_datos": None, "valor_esperado": None, "orden": 2},
        {"id": 5, "padre_id": 4, "tipo": "atomic", "operador": "in",
         "fuente_datos": "invoice.codigo", "valor_esperado": SALA_CODES,
         "orden": 0},
    ]


def _row_7h(codigo: str = "890701", factura: str = "F001",
            tipo: str = "Urgencias",
            cierre: str = "2026-06-24 15:00:00") -> dict:
    return {"numero_factura": factura, "codigo": codigo,
            "tipo_factura_descripcion": tipo,
            "fec_factura": "2026-06-24 08:00:00", "fecha_cierre": cierre}


def _cond_mocks(conds: list[dict]) -> list:
    mocks = []
    for c in conds:
        m = MagicMock()
        for k, v in c.items():
            setattr(m, k, v)
        mocks.append(m)
    return mocks


def _engine_with(rule_parametros: list[dict], conds: list[dict]):
    """Engine con sesion mockeada: regla + condiciones inyectadas."""
    from app.models import Regla
    from app.services.engine.engine import RuleEvaluationEngine

    rule = Regla(
        id=44, nombre="sala_obs_mayor_6_horas", dominio="urgencias",
        estado="active", version=1, prioridad=32, severidad="warning",
        descripcion="Sala obs > 6h", parametros=rule_parametros,
    )
    session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.first.return_value = rule
    mock_query.all.return_value = _cond_mocks(conds)
    session.query.return_value = mock_query
    return RuleEvaluationEngine(session)


def _eval_bare(rows_list: list[dict]) -> list[dict]:
    engine = _engine_with([dict(BARE_PARAM)], _conds_44())
    return engine.evaluate_sheet(
        "sala_obs_mayor_6_horas", None, {}, rows=rows_list,
        persist=False, dominio="urgencias",
    )


class TestInferencia44Bare:
    def test_7h_sin_sala_un_match(self):
        results = _eval_bare([_row_7h("890701")])
        assert len(results) == 1
        assert results[0]["factura"] == "F001"

    def test_con_codigo_sala_no_match(self):
        assert _eval_bare([_row_7h("5DSB01")]) == []

    def test_3h_no_match(self):
        rows = [_row_7h("890701", cierre="2026-06-24 11:00:00")]
        assert _eval_bare(rows) == []

    def test_materializa_estancia_horas(self):
        """La agregacion inferida compute_horas viaja en el problema."""
        results = _eval_bare([_row_7h("890701")])
        assert len(results) == 1
        assert results[0].get("estancia_horas") == pytest.approx(7.0)

    def test_materializa_collect_set_codigo(self):
        results = _eval_bare([_row_7h("890701")])
        assert len(results) == 1
        assert "890701" in results[0].get("collect_set_codigo", [])

    def test_prefiltra_tipo_factura_antedel_grupo(self):
        """Fila Hospitalizacion se descarta pre-grupo aunque abra el grupo.

        Sin inferencia, el escalar de la primera fila (Hospitalizacion)
        tumbaria el eq y daria NO_MATCH. Con prefiltro, la fila se
        descarta y la fila Urgencias 7h hace MATCH.
        """
        rows = [_row_7h("890701", tipo="Hospitalización"),
                _row_7h("890701", tipo="Urgencias")]
        results = _eval_bare(rows)
        assert len(results) == 1
        assert results[0]["factura"] == "F001"

    def test_prefiltro_descarta_factura_entera_no_match(self):
        rows = [_row_7h("890701", tipo="Hospitalización")]
        assert _eval_bare(rows) == []


class TestResolucionUnitaria:
    def test_infiere_aggs_y_prefiltro(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        tree = ConditionEvaluator().build_tree(_conds_44())
        aggs, f_field, f_value = GroupEvaluator.resolve_group_config(
            tree, dict(BARE_PARAM))
        targets = {a.get("target") for a in aggs}
        assert "estancia_horas" in targets
        assert "collect_set_codigo" in targets
        assert f_field == "tipo_factura_descripcion"
        assert f_value == "Urgencias"

    def test_literal_con_comillas_tambien_infiere(self):
        """valor_esperado '"Urgencias"' (forma JSONB) infiere igual."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        conds = _conds_44()
        conds[2] = dict(conds[2], valor_esperado='"Urgencias"')
        tree = ConditionEvaluator().build_tree(conds)
        _, f_field, f_value = GroupEvaluator.resolve_group_config(
            tree, dict(BARE_PARAM))
        assert (f_field, f_value) == ("tipo_factura_descripcion", "Urgencias")

    def test_sin_fuentes_grupo_no_infiere_nada(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        conds = [{"id": 1, "padre_id": None, "tipo": "atomic",
                  "operador": "eq", "fuente_datos": "invoice.convenio_facturado",
                  "valor_esperado": "PyP", "orden": 0}]
        tree = ConditionEvaluator().build_tree(conds)
        aggs, _, _ = GroupEvaluator.resolve_group_config(
            tree, dict(BARE_PARAM))
        assert aggs == []


class TestExplicitosMandan:
    def test_agg_explicita_no_se_duplica(self):
        """Param con compute_horas explicito: convive, sin duplicar target."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        tree = ConditionEvaluator().build_tree(_conds_44())
        param = {"group_by": "numero_factura", "aggregations": [
            {"function": "compute_horas", "field1": "fec_factura",
             "field2": "fecha_cierre", "target": "estancia_horas"}]}
        aggs, _, _ = GroupEvaluator.resolve_group_config(tree, param)
        assert [a.get("target") for a in aggs].count("estancia_horas") == 1

    def test_filter_explicito_no_se_sobrescribe(self):
        """filter_field/value explicitos mandan sobre el inferido."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        tree = ConditionEvaluator().build_tree(_conds_44())
        param = {"group_by": "numero_factura",
                 "filter_field": "tipo_factura_descripcion",
                 "filter_value": "Hospitalización", "aggregations": []}
        _, f_field, f_value = GroupEvaluator.resolve_group_config(
            tree, param)
        assert (f_field, f_value) == (
            "tipo_factura_descripcion", "Hospitalización")

    def test_doble_tipo_explicito_intacto(self):
        """Doble-tipo con distinct_count explicito sigue matcheando (2 tipos)."""
        from app.models import Regla
        from app.services.engine.engine import RuleEvaluationEngine

        rule = Regla(
            id=1, nombre="doble_tipo_procedimiento", dominio="transversal",
            estado="active", version=1, prioridad=10, severidad="error",
            descripcion="Doble tipo", parametros=[{
                "group_by": "numero_factura",
                "aggregations": [{"function": "distinct_count",
                                  "field": "tipo_procedimiento",
                                  "target": "distinct_count_tipo_procedimiento"}]}],
        )
        cond = MagicMock()
        cond.id = 1; cond.regla_id = 1; cond.padre_id = None
        cond.tipo = "atomic"; cond.operador = "gt"
        cond.fuente_datos = "invoice.distinct_count_tipo_procedimiento"
        cond.valor_esperado = "1"; cond.orden = 0
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = rule
        mock_query.all.return_value = [cond]
        session.query.return_value = mock_query
        engine = RuleEvaluationEngine(session)
        rows = [{"numero_factura": "F001", "tipo_procedimiento": "02"},
                {"numero_factura": "F001", "tipo_procedimiento": "03"}]
        results = engine.evaluate_sheet(
            "doble_tipo_procedimiento", None, {}, rows=rows, persist=False)
        assert len(results) == 1
        assert results[0]["factura"] == "F001"
