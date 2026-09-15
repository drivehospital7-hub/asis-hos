"""Unit tests for HospiSalaObsCantidadCheckEvaluator.

Strict TDD: tests written BEFORE implementation.
Operator: hospi_sala_obs_cantidad_check

User decisions (verbatim):
- Sin gate: formula 1+floor(h/24) para cualquier estancia
  (12h->1, 24h->2, 36h->2, 48h->3).
- MATCH si cant_38114 != esperada (faltante o sobrante).
- Sin fila 38114 -> sum=0 -> MATCH (falta el codigo).
- Tarifario debe ser Soat y tipo Hospitalizacion
  (gate explicito en arbol + re-chequeo en evaluator).
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


def _group_ctx(rows: list[dict]) -> EvaluationContext:
    first = dict(rows[0]) if rows else {}
    return EvaluationContext(invoice_data=first, group_rows=rows)


def _row_ctx(row: dict) -> EvaluationContext:
    return EvaluationContext(invoice_data=dict(row), group_rows=None)


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

    # ── Gate tarifario ──
    def test_tarifario_no_soat_no_match(self, evaluator):
        ctx = _group_ctx([_row(48, "38114", 0, tarifario="Subsidiado")])
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_tipo_no_hosp_no_match(self, evaluator):
        ctx = _group_ctx([_row(48, "38114", 0, tipo="Urgencias")])
        assert evaluator.evaluate({}, None, None, ctx) is False

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
