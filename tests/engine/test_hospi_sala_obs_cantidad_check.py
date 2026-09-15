"""Unit tests for HospiSalaObsCantidadCheckEvaluator.

Strict TDD: tests written BEFORE implementation.
Operator: hospi_sala_obs_cantidad_check

User decisions (verbatim):
- Sin gate interno: formula 1+floor(h/24) para cualquier estancia
  (12h->1, 24h->2, 36h->2, 48h->3).
- MATCH si cant_codigo_objetivo != esperada (faltante o sobrante).
- Sin fila del codigo objetivo -> sum=0 -> MATCH (falta el codigo).
- El gate de tarifario/tipo vive en el arbol (eq), NO en el evaluator.
  El evaluator solo lee codigo_objetivo de params (default 38114).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.engine.context import EvaluationContext


BASE = datetime(2024, 1, 15, 8, 0, 0)


def _row(hours_after: float = 0.0, codigo: str = "38114", cantidad=1,
         tarifario: str = "Soat", tipo: str = "Hospitalización",
         base: datetime = BASE) -> dict:
    return {
        "fec_factura": base,
        "fecha_cierre": base + timedelta(hours=hours_after),
        "codigo": codigo,
        "cantidad": cantidad,
        "tarifario": tarifario,
        "tipo_factura_descripcion": tipo,
    }


def _group_ctx(rows: list[dict], params: dict | None = None) -> EvaluationContext:
    first = dict(rows[0]) if rows else {}
    ctx = EvaluationContext(invoice_data=first, group_rows=rows)
    if params is not None:
        ctx.params = params
    return ctx


def _row_ctx(row: dict, params: dict | None = None) -> EvaluationContext:
    ctx = EvaluationContext(invoice_data=dict(row), group_rows=None)
    if params is not None:
        ctx.params = params
    return ctx


CUPS_PARAMS = {"codigo_objetivo": "129B02"}


@pytest.fixture
def evaluator():
    from app.services.engine.evaluators import EVALUATOR_REGISTRY
    return EVALUATOR_REGISTRY["hospi_sala_obs_cantidad_check"]


class TestHospiSalaObsCantidadCheck:
    # ── 12h -> esperada 1 ──
    def test_12h_cant0_match(self, evaluator):
        ctx = _group_ctx([_row(12, "999999", 1), _row(12, "890601", 1)])
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_12h_cant2_match(self, evaluator):
        ctx = _group_ctx([_row(12, "38114", 2)])
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_12h_cant1_no_match(self, evaluator):
        ctx = _group_ctx([_row(12, "38114", 1)])
        assert evaluator.evaluate({}, None, None, ctx) is False

    # ── 24h -> esperada 2 ──
    def test_24h_cant2_no_match(self, evaluator):
        ctx = _group_ctx([_row(24, "38114", 2)])
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_24h_cant1_match(self, evaluator):
        ctx = _group_ctx([_row(24, "38114", 1)])
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── 36h -> esperada 2 ──
    def test_36h_cant2_no_match(self, evaluator):
        ctx = _group_ctx([_row(36, "38114", 2)])
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_36h_cant3_match(self, evaluator):
        ctx = _group_ctx([_row(36, "38114", 3)])
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── 48h -> esperada 3 ──
    def test_48h_cant3_no_match(self, evaluator):
        ctx = _group_ctx([_row(48, "38114", 1), _row(48, "38114", 2)])
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_48h_cant2_match(self, evaluator):
        ctx = _group_ctx([_row(48, "38114", 2)])
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── Sin gate interno: tarifario/tipo los filtra el arbol ──
    def test_sin_gate_interno_tarifario_distinto_si_cuenta(self, evaluator):
        # Evaluator puro: factura Subsidiado con 38114 cant 0 a 48h
        # (esperada 3) -> MATCH; el arbol descarta por tarifario.
        ctx = _group_ctx([_row(48, "38114", 0, tarifario="Subsidiado")])
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_sin_gate_interno_tipo_distinto_si_cuenta(self, evaluator):
        # Evaluator puro: tipo Urgencias con 38114 cant 0 a 48h
        # (esperada 3) -> MATCH; el arbol descarta por tipo/tarifario.
        ctx = _group_ctx([_row(48, "38114", 0, tipo="Urgencias")])
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── Sin par fechas ──
    def test_sin_par_fechas_no_match(self, evaluator):
        bad = _row(12, "38114", 0)
        bad["fecha_cierre"] = None
        ctx = _group_ctx([bad])
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_fechas_invalidas_no_match(self, evaluator):
        bad = _row(12, "38114", 5)
        bad["fec_factura"] = "no-fecha"
        bad["fecha_cierre"] = "tampoco"
        ctx = _group_ctx([bad])
        assert evaluator.evaluate({}, None, None, ctx) is False

    # ── Modo fila única ──
    def test_row_mode_match(self, evaluator):
        ctx = _row_ctx(_row(12, "38114", 2))
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_row_mode_no_match(self, evaluator):
        ctx = _row_ctx(_row(12, "38114", 1))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_row_mode_sin_38114_match(self, evaluator):
        ctx = _row_ctx(_row(12, "999999", 3))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── Edge ──
    def test_no_context_false(self, evaluator):
        assert evaluator.evaluate({}, None, None, None) is False

    def test_empty_group_no_match(self, evaluator):
        ctx = EvaluationContext(invoice_data={}, group_rows=[])
        assert evaluator.evaluate({}, None, None, ctx) is False


class TestHospiSalaObsCupsCantidad:
    """Gemela Cups: codigo_objetivo=129B02 via ctx.params.

    El gate de tarifario/tipo vive en el arbol; el evaluator solo suma
    el codigo objetivo. Formula identica: esperada = 1+floor(h/24).
    """

    # ── 24h -> esperada 2 (casos gemelos exigidos) ──
    def test_24h_cant1_match(self, evaluator):
        ctx = _group_ctx([_row(24, "129B02", 1, tarifario="Cups")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_24h_cant2_no_match(self, evaluator):
        ctx = _group_ctx([_row(24, "129B02", 2, tarifario="Cups")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is False

    # ── 12h -> esperada 1 ──
    def test_12h_cant1_no_match(self, evaluator):
        ctx = _group_ctx([_row(12, "129B02", 1, tarifario="Cups")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_12h_cant0_match(self, evaluator):
        ctx = _group_ctx([_row(12, "999999", 1, tarifario="Cups")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── codigo_objetivo case-insensitive ──
    def test_codigo_objetivo_minusculas_match(self, evaluator):
        params = {"codigo_objetivo": "129b02"}
        ctx = _group_ctx([_row(24, "129B02", 1, tarifario="Cups")], params)
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── Sin gate interno: el evaluator ignora tarifario ──
    def test_tarifario_distinto_igual_cuenta(self, evaluator):
        # Misma fila Cups vs Soat: el evaluator suma igual (gate = arbol).
        ctx = _group_ctx([_row(24, "129B02", 1, tarifario="Soat")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_codigo_soat_con_params_cups_es_faltante(self, evaluator):
        # Solo hay 38114: suma 129B02 = 0 != esperada 2 -> MATCH (falta codigo).
        ctx = _group_ctx([_row(24, "38114", 2, tarifario="Cups")], CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── Modo fila unica ──
    def test_row_mode_cups_match(self, evaluator):
        ctx = _row_ctx(_row(24, "129B02", 1, tarifario="Cups"), CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_row_mode_cups_no_match(self, evaluator):
        ctx = _row_ctx(_row(24, "129B02", 2, tarifario="Cups"), CUPS_PARAMS)
        assert evaluator.evaluate({}, None, None, ctx) is False


class TestHospiSalaObsDefaultSinParams:
    """Sin params -> codigo default 38114 (regla Soat intacta)."""

    def test_params_none_usa_defaults(self, evaluator):
        ctx = _group_ctx([_row(24, "38114", 2)], None)
        assert evaluator.evaluate({}, None, None, ctx) is False
        ctx = _group_ctx([_row(24, "38114", 1)], None)
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_params_vacio_usa_defaults(self, evaluator):
        ctx = _group_ctx([_row(24, "38114", 2)], {})
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_params_sin_codigo_usa_default_38114(self, evaluator):
        # Params sin codigo_objetivo -> default 38114; fila 38114 cant 1
        # a 24h (esperada 2) -> MATCH.
        ctx = _group_ctx([_row(24, "38114", 1, tarifario="Cups")],
                         {"group_by": "numero_factura"})
        assert evaluator.evaluate({}, None, None, ctx) is True

    def test_solo_codigo_cambia_objetivo(self, evaluator):
        # Params con codigo 129B02; fila Soat/129B02 cant 1 a 24h ->
        # suma 129B02 = 1 != 2 -> MATCH (tarifario lo gatea el arbol).
        ctx = _group_ctx([_row(24, "129B02", 1)], {"codigo_objetivo": "129B02"})
        assert evaluator.evaluate({}, None, None, ctx) is True


class TestHospiSalaObsParamsForwarding:
    """El engine debe llevar rule.parametros[0] hasta el evaluator (group)."""

    def _run_group(self, rows: list[dict], param_config: dict | None):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        from app.services.engine.group_evaluator import GroupEvaluator

        ce = ConditionEvaluator()
        tree = ce.build_tree([{
            "id": 1, "padre_id": None, "tipo": "atomic",
            "operador": "hospi_sala_obs_cantidad_check",
            "fuente_datos": "invoice.cantidad",
            "valor_esperado": None, "orden": 0,
        }])
        groups = None
        for r in rows:
            r.setdefault("numero_factura", "F001")
        groups = GroupEvaluator.build_groups(
            None, {}, "numero_factura", None, None, rows=rows,
        )
        return GroupEvaluator.evaluate(
            groups=groups, data_sheet=None, indices={},
            agg_configs=[], condition_tree=tree,
            condition_evaluator=ce,
            rule_info={"id": 0, "version": 1, "dominio": "hospitalizacion",
                       "nombre": "x", "descripcion": "x", "severidad": "error"},
            evidence_collector=None, record_evidence=False,
            rows=rows, param_config=param_config,
        )

    def test_con_params_cups_match(self):
        rows = [_row(24, "129B02", 1, tarifario="Cups")]
        results = self._run_group(rows, dict(CUPS_PARAMS))
        assert len(results) == 1

    def test_sin_params_cuenta_38114_por_default(self):
        # Sin params el objetivo es 38114: fila Cups/129B02 cant 1 a 24h
        # -> suma 38114 = 0 != 2 -> MATCH (regla Soat intacta por default).
        rows = [_row(24, "129B02", 1, tarifario="Cups")]
        results = self._run_group(rows, None)
        assert len(results) == 1

    def test_soat_sin_params_no_match(self):
        # Verificacion soat-rule intacta: Soat/38114 cant 2 a 24h
        # (esperada 2) sin params -> NO_MATCH.
        rows = [_row(24, "38114", 2)]
        results = self._run_group(rows, None)
        assert results == []


class TestHospiSalaObsBaseDias:
    """Modo dias: params base (default 1) -> esperada = base + floor(h/24).

    Con base=0 la esperada equivale a dias completos:
    <24h->0, 24h->1, 36h->1, 49h->2.
    Sin base en params -> comportamiento actual identico (base=1).
    """

    DIAS_PARAMS = {"codigo_objetivo": "39131", "base": 0}

    # ── base=0: <24h -> esperada 0 ──
    def test_base0_12h_cant0_no_match(self, evaluator):
        ctx = _group_ctx([_row(12, "39131", 0)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_base0_12h_cant1_match(self, evaluator):
        ctx = _group_ctx([_row(12, "39131", 1)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── base=0: 24h -> esperada 1 ──
    def test_base0_24h_cant1_no_match(self, evaluator):
        ctx = _group_ctx([_row(24, "39131", 1)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_base0_24h_cant2_match(self, evaluator):
        ctx = _group_ctx([_row(24, "39131", 2)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── base=0: 36h -> esperada 1 ──
    def test_base0_36h_cant1_no_match(self, evaluator):
        ctx = _group_ctx([_row(36, "39131", 1)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_base0_36h_cant2_match(self, evaluator):
        ctx = _group_ctx([_row(36, "39131", 2)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── base=0: 49h -> esperada 2 ──
    def test_base0_49h_cant2_no_match(self, evaluator):
        ctx = _group_ctx([_row(49, "39131", 2)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_base0_49h_cant1_match(self, evaluator):
        ctx = _group_ctx([_row(49, "39131", 1)], dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── base explicito 1 == default (regresion modo actual) ──
    def test_base1_igual_default_24h(self, evaluator):
        params = {"codigo_objetivo": "38114", "base": 1}
        ctx = _group_ctx([_row(24, "38114", 2)], dict(params))
        assert evaluator.evaluate({}, None, None, ctx) is False
        ctx = _group_ctx([_row(24, "38114", 1)], dict(params))
        assert evaluator.evaluate({}, None, None, ctx) is True

    # ── row mode con base=0 ──
    def test_row_mode_base0_no_match(self, evaluator):
        ctx = _row_ctx(_row(36, "39131", 1), dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_row_mode_base0_match(self, evaluator):
        ctx = _row_ctx(_row(36, "39131", 0), dict(self.DIAS_PARAMS))
        assert evaluator.evaluate({}, None, None, ctx) is True
