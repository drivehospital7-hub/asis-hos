"""Unit tests for RevisionCantidadUrgenciasEvaluator.

Strict TDD: tests written BEFORE implementation.
Operator: revision_cantidad_urgencias_check

Cascade logic (matches detect_revision_cantidad_urgencias legacy):
1. Check CODIGOS_REVISION_CANTIDAD_EXENTOS → NO_MATCH
2. Check CODIGOS_LIMITE_ESPECIFICO → if cantidad <= limit, NO_MATCH
3. tipo=02 + Lab=No → Cant > 2 (codigo=903883: Cant > 5)
4. tipo in 09/12 → Cant > 20 (codigo=V03AN0101: always NO_MATCH)
5. General → Cant > 1
"""

from __future__ import annotations

import pytest

from app.services.engine.context import EvaluationContext


def _make_context(invoice_data: dict | None = None) -> EvaluationContext:
    """Helper to build an EvaluationContext with invoice data."""
    return EvaluationContext(invoice_data=invoice_data or {})


class TestRevisionCantidadUrgenciasEvaluator:
    """Tests for RevisionCantidadUrgenciasEvaluator."""

    # ── Helper to get the evaluator ──────────────────────────────────────

    @pytest.fixture
    def evaluator(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        return EVALUATOR_REGISTRY["revision_cantidad_urgencias_check"]

    # ── R1: General excess ──────────────────────────────────────────────

    def test_general_excess(self, evaluator):
        """Cantidad=3 (>1), no exceptions → MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, 3, None, ctx) is True

    def test_general_no_excess(self, evaluator):
        """Cantidad=1 (≤1), no exceptions → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, 1, None, ctx) is False

    # ── R2: Exempt code ─────────────────────────────────────────────────

    def test_exempt_code_no_match(self, evaluator):
        """CODIGOS_REVISION_CANTIDAD_EXENTOS → NO_MATCH even with high cantidad."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890601",  # Exempt code
        })
        assert evaluator.evaluate({}, 100, None, ctx) is False

    def test_exempt_code_low_cantidad(self, evaluator):
        """Exempt code with cantidad=1 → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "129B02",  # Exempt code
        })
        assert evaluator.evaluate({}, 1, None, ctx) is False

    # ── R3: Specific limit OK ───────────────────────────────────────────

    def test_specific_limit_ok(self, evaluator):
        """codigo in CODIGOS_LIMITE_ESPECIFICO, cantidad <= limit → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "939403",  # Specific limit = 2
        })
        assert evaluator.evaluate({}, 2, None, ctx) is False

    def test_specific_limit_exceeded(self, evaluator):
        """codigo in CODIGOS_LIMITE_ESPECIFICO, cantidad > limit → fall through to cascade."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "939402",  # Specific limit = 8
        })
        # cantidad=9 > 8 → exceeds specific limit → falls through to general (6 → Cant > 1) → MATCH
        assert evaluator.evaluate({}, 9, None, ctx) is True

    # ── R4: 02+Lab=No excess ────────────────────────────────────────────

    def test_02_lab_no_excess(self, evaluator):
        """tipo=02, Lab=No, Cant=3 (>2) → MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "02",
            "laboratorio": "No",
            "codigo": "902210",
        })
        assert evaluator.evaluate({}, 3, None, ctx) is True

    def test_02_lab_no_ok(self, evaluator):
        """tipo=02, Lab=No, Cant=2 (≤2) → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "02",
            "laboratorio": "No",
            "codigo": "902210",
        })
        assert evaluator.evaluate({}, 2, None, ctx) is False

    def test_02_lab_no_903883_excess(self, evaluator):
        """tipo=02, Lab=No, codigo=903883, Cant=6 (>5) → MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "02",
            "laboratorio": "No",
            "codigo": "903883",
        })
        assert evaluator.evaluate({}, 6, None, ctx) is True

    def test_02_lab_no_903883_ok(self, evaluator):
        """tipo=02, Lab=No, codigo=903883, Cant=5 (≤5) → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "02",
            "laboratorio": "No",
            "codigo": "903883",
        })
        assert evaluator.evaluate({}, 5, None, ctx) is False

    # ── R5: 09/12 excess ────────────────────────────────────────────────

    def test_09_12_excess(self, evaluator):
        """tipo=09, Cant=21 (>20) → MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "09",
            "laboratorio": "Si",
            "codigo": "998101",
        })
        assert evaluator.evaluate({}, 21, None, ctx) is True

    def test_09_12_ok(self, evaluator):
        """tipo=12, Cant=20 (≤20) → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "12",
            "laboratorio": "Si",
            "codigo": "998101",
        })
        assert evaluator.evaluate({}, 20, None, ctx) is False

    def test_v03an0101_exempt(self, evaluator):
        """codigo=V03AN0101, any cantidad (even 999) → always NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "09",
            "laboratorio": "Si",
            "codigo": "V03AN0101",
        })
        assert evaluator.evaluate({}, 999, None, ctx) is False

    def test_v03an0101_cantidad_1(self, evaluator):
        """codigo=V03AN0101, Cant=1 → NO_MATCH."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "09",
            "laboratorio": "Si",
            "codigo": "V03AN0101",
        })
        assert evaluator.evaluate({}, 1, None, ctx) is False

    # ── R6: Non-Urgencias → SKIP ────────────────────────────────────────

    def test_non_urgencias_skipped(self, evaluator):
        """tipo_factura='Consultas' → NO_MATCH (skip)."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Consultas",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, 5, None, ctx) is False

    def test_intramural_skipped(self, evaluator):
        """tipo_factura='Intramural' → NO_MATCH (skip)."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Intramural",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, 5, None, ctx) is False

    # ── R7: Edge cases ──────────────────────────────────────────────────

    def test_no_context_returns_false(self, evaluator):
        """Without context, evaluate returns False gracefully."""
        assert evaluator.evaluate({}, 3, None, None) is False

    def test_none_cantidad_returns_false(self, evaluator):
        """None cantidad → False."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, None, None, ctx) is False

    def test_cantidad_string_coerced(self, evaluator):
        """Cantidad as string '3' → coerced to float, MATCH if > threshold."""
        ctx = _make_context({
            "tipo_factura_descripcion": "Urgencias",
            "codigo_tipo_procedimiento": "06",
            "laboratorio": "Si",
            "codigo": "890201",
        })
        assert evaluator.evaluate({}, "3", None, ctx) is True

    def test_missing_invoice_data_returns_false(self, evaluator):
        """Empty invoice_data dict → all lookups return empty → no match."""
        ctx = _make_context({})
        assert evaluator.evaluate({}, 3, None, ctx) is False
