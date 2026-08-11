"""Tests for CupsContratadoEvaluator — 6 exception branches + edge cases.

Strict TDD: tests written first, then implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.engine.context import EvaluationContext


# ── Constants ──────────────────────────────────────────────────────────────

FACTURADOR_NAME = "MEZA FERNANDEZ CARLOS OMAR"
VALOR_TARIFARIO_FARMACIA = "Suminstros, Medicamentos"


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session that returns empty data.

    Each test can override the .all() side_effect to set up specific data.
    """
    session = MagicMock()
    mock_query = MagicMock()
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []
    session.query.return_value = mock_query
    return session


def make_context(invoice_data: dict | None = None, session=None) -> EvaluationContext:
    """Create an EvaluationContext with optional invoice data and session."""
    return EvaluationContext(
        invoice_data=invoice_data or {},
        session=session,
    )


def make_evaluator():
    """Create a fresh CupsContratadoEvaluator instance."""
    from app.services.engine.evaluators import CupsContratadoEvaluator
    return CupsContratadoEvaluator()


# ── Tests: Farmacia Skip (Branch 1) ──────────────────────────────────────

class TestFarmaciaSkip:
    """Branch 1: tarifario == 'Suminstros, Medicamentos' → skip."""

    def test_farmacia_tarifario_returns_true(self):
        """tarifario farmacia → evaluator returns True (skip)."""
        evaluator = make_evaluator()
        ctx = make_context({"tarifario": VALOR_TARIFARIO_FARMACIA})
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "Farmacia tarifario should skip (return True)"

    def test_non_farmacia_tarifario_proceeds(self):
        """Non-farmacia tarifario → does not skip, proceeds to next check."""
        evaluator = make_evaluator()
        # No session loaded → should hit the no-session path and return False
        ctx = make_context({"tarifario": "SOAT"})
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is False, "Non-farmacia without DB should return False"

    def test_farmacia_tarifario_with_no_invoice_data(self):
        """Empty invoice_data → no tarifario → proceeds to next checks."""
        evaluator = make_evaluator()
        ctx = make_context({})
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is False, "Empty invoice_data without DB should return False"


# ── Tests: Urgencias Facturador (Branch 2) ───────────────────────────────

class TestUrgenciasFacturador:
    """Branch 2: responsable_cierra in FACTURADORES_URGENCIAS + codigo in nota_urgencias_cups."""

    def test_urgencias_facturador_cups_in_nota_returns_true(self):
        """Facturador with CUPS in nota_hoja 1/27 → True (skip)."""
        evaluator = make_evaluator()
        # Pre-load with urgencias data
        evaluator._loaded = True
        evaluator._nota_urgencias_cups = {"CUPS_URG01"}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "responsable_cierra": FACTURADOR_NAME,
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS_URG01", None, ctx)
        assert result is True, "Facturador with CUPS in nota_hoja should skip"

    def test_urgencias_facturador_cups_not_in_nota_proceeds(self):
        """Facturador but CUPS not in nota_hoja → proceeds to next checks."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_urgencias_cups = {"CUPS_URG01"}
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "responsable_cierra": FACTURADOR_NAME,
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "OTHER_CUPS", None, ctx)
        # CUPS not in nota_urgencias → proceeds → entity in DB → pares check fails → False
        assert result is False, "Facturador with CUPS NOT in nota_hoja should not skip"

    def test_urgencias_facturador_normalized_name(self):
        """Facturador name with extra spaces is normalized."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_urgencias_cups = {"CUPS_URG01"}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "responsable_cierra": "  MEZA   FERNANDEZ   CARLOS   OMAR  ",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS_URG01", None, ctx)
        assert result is True, "Normalized facturador name should match"

    def test_non_facturador_responsable_proceeds(self):
        """Non-facturador responsable_cierra → proceeds."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_urgencias_cups = {"CUPS_URG01"}
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "responsable_cierra": "OTRA PERSONA",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS_URG01", None, ctx)
        # Not a facturador → not skipped by urgencias → proceeds → entity in DB → pares fails → False
        assert result is False, "Non-facturador should not skip via urgencias branch"


# ── Tests: CAP + ESS118 (Branch 3) ───────────────────────────────────────

class TestCapEss118:
    """Branch 3: CAP invoice + ESS118 → check nota_cap_cups[3] only."""

    def test_cap_ess118_cups_in_nota3_returns_true(self):
        """CAP + ESS118 + CUPS in nota_cap[3] → True."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {3: {"CAP_CUPS_A", "CAP_CUPS_B"}}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_A", None, ctx)
        assert result is True, "CAP + ESS118 + CUPS in nota_cap[3] should be valid"

    def test_cap_ess118_cups_not_in_nota3_returns_false(self):
        """CAP + ESS118 + CUPS NOT in nota_cap[3] → False (error)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {3: {"CAP_CUPS_A"}}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_Z", None, ctx)
        assert result is False, "CAP + ESS118 + CUPS NOT in nota_cap[3] should error"

    def test_cap_ess118_empty_nota3_returns_false(self):
        """CAP + ESS118 + no nota_cap[3] data → False (error)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {2: {"CAP_CUPS_A"}}  # Only nota 2, not 3
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_A", None, ctx)
        assert result is False, "CAP + ESS118 + empty nota_cap[3] should error"

    def test_non_cap_ess118_no_entidad_skips_branch(self):
        """Non-ESS118 entity with CAP invoice → proceeds, then entity check skips."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118", "EPSS41"}  # EPS012 not in DB
        ctx = make_context({
            "codigo_entidad_cobrar": "EPS012",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "ANY_CUPS", None, ctx)
        # Proceeds past CAP check → entity not in DB → skip (True)
        assert result is True, "EPS012 not in entidades_con_datos should skip"


# ── Tests: CAP + EPSS41 (Branch 4) ───────────────────────────────────────

class TestCapEpss41:
    """Branch 4: CAP invoice + EPSS41 → check nota_cap_cups[2] only."""

    def test_cap_epss41_cups_in_nota2_returns_true(self):
        """CAP + EPSS41 + CUPS in nota_cap[2] → True."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {2: {"CAP_CUPS_X"}}
        ctx = make_context({
            "codigo_entidad_cobrar": "EPSS41",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_X", None, ctx)
        assert result is True, "CAP + EPSS41 + CUPS in nota_cap[2] should be valid"

    def test_cap_epss41_cups_not_in_nota2_returns_false(self):
        """CAP + EPSS41 + CUPS NOT in nota_cap[2] → False (error)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {2: {"CAP_CUPS_X"}}
        ctx = make_context({
            "codigo_entidad_cobrar": "EPSS41",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_Y", None, ctx)
        assert result is False, "CAP + EPSS41 + CUPS NOT in nota_cap[2] should error"

    def test_cap_epss41_empty_nota2_returns_false(self):
        """CAP + EPSS41 + no nota_cap[2] data → False (error)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_cap_cups = {}  # Empty
        ctx = make_context({
            "codigo_entidad_cobrar": "EPSS41",
            "numero_factura": "CAP-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CAP_CUPS_X", None, ctx)
        assert result is False, "CAP + EPSS41 + empty nota_cap[2] should error"


# ── Tests: Entidad sin datos (Branch 5) ──────────────────────────────────

class TestEntidadSinDatos:
    """Branch 5: cod_entidad not in entidades_con_datos → skip."""

    def test_unknown_entity_skipped(self):
        """Entidad not in DB → True (skip)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118", "EPS012"}
        ctx = make_context({
            "codigo_entidad_cobrar": "UNKNOWN_ENT",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "Unknown entity should be skipped (return True)"

    def test_known_entity_proceeds_to_pares_validos(self):
        """Known entity (in entidades_con_datos) → proceeds to pares_validos check."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is False, "Known entity without pares_validos should return False"


# ── Tests: Pares Válidos (Branches 6-7) ──────────────────────────────────

class TestParesValidos:
    """Branches 6-7: Check pares_validos and codigo_equiv fallback."""

    def test_pares_validos_match_returns_true(self):
        """(entidad, codigo) in pares_validos → True."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = {("ESS118", "CUPS001")}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "Contracted pair should return True"

    def test_pares_validos_no_match_returns_false(self):
        """(entidad, codigo) NOT in pares_validos → False."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = {("ESS118", "CUPS001")}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS999", None, ctx)
        assert result is False, "Non-contracted pair should return False"

    def test_codigo_equiv_fallback_returns_true(self):
        """codigo not in pares, but codigo_equiv is → True."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = {("ESS118", "EQUIV_CUPS")}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "codigo_equiv": "EQUIV_CUPS",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "codigo_equiv fallback should return True"

    def test_codigo_equiv_empty_still_false(self):
        """codigo not in pares, codigo_equiv is empty → False."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = {("ESS118", "CUPS001")}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "codigo_equiv": "",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS999", None, ctx)
        assert result is False, "Empty codigo_equiv should not match"

    def test_codigo_equiv_missing_column_still_false(self):
        """codigo not in pares, no codigo_equiv on context → False."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = {("ESS118", "CUPS001")}
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS999", None, ctx)
        assert result is False, "Missing codigo_equiv should not match"


# ── Tests: FEV Autorizado (Branch 8) ─────────────────────────────────────

class TestFevAutorizado:
    """Branch 8: factura starts with FEV + entidad in (EPS037, EPSS41) → skip."""

    def test_fev_eps037_returns_true(self):
        """FEV + EPS037 → True (skip)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"EPS037"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "EPS037",
            "numero_factura": "FEV-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "FEV + EPS037 should be authorized"

    def test_fev_epss41_returns_true(self):
        """FEV + EPSS41 → True (skip)."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"EPSS41"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "EPSS41",
            "numero_factura": "FEV-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is True, "FEV + EPSS41 should be authorized"

    def test_fev_other_entity_returns_false(self):
        """FEV + other entity → not authorized, proceed to pares_validos check."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "FEV-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is False, "FEV + other entity should not be authorized"

    def test_non_fev_factura_proceeds(self):
        """Non-FEV factura → proceeds normal check."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"EPS037"}
        evaluator._pares_validos = set()
        ctx = make_context({
            "codigo_entidad_cobrar": "EPS037",
            "numero_factura": "REG-001",
        })
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert result is False, "Non-FEV factura should not trigger FEV exception"


# ── Tests: Edge Cases ────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases for the evaluator."""

    def test_context_is_none_returns_false(self):
        """No context → False (cannot assume contracted)."""
        evaluator = make_evaluator()
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, None)
        assert result is False, "No context should return False"

    def test_preload_data_called_on_first_evaluate(self):
        """First evaluate() with session triggers _preload_data."""
        evaluator = make_evaluator()
        assert evaluator._loaded is False, "Should not be loaded initially"
        session = MagicMock()
        # Mock query chain
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.side_effect = [[], [], [], []]  # Empty results for all 4 queries
        session.query.return_value = mock_query

        # Use a non-farmacia context that requires DB access
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "CAP-001",
        }, session=session)
        evaluator.evaluate({"operador": "cups_contratado"}, "CUPS001", None, ctx)
        assert evaluator._loaded is True, "Should be loaded after first evaluate()"

    def test_codigo_none_returns_false(self):
        """None row_value → False."""
        evaluator = make_evaluator()
        ctx = make_context({})
        result = evaluator.evaluate({"operador": "cups_contratado"}, None, None, ctx)
        assert result is False, "None codigo should return False"

    def test_evaluator_operator_defined(self):
        """Evaluator operator is 'cups_contratado'."""
        evaluator = make_evaluator()
        assert evaluator.operator == "cups_contratado"


# ── Tests: Full Exception Chain Order ────────────────────────────────────

class TestExceptionChainOrder:
    """Verify the chain order matches legacy: farmacia → urgencias → CAP → entidad → pares → FEV."""

    def test_farmacia_check_before_urgencias(self):
        """Farmacia skip is checked BEFORE urgencias facturador check."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._nota_urgencias_cups = {"SOME_CUPS"}
        # If farmacia check comes first, it should skip even with urgencias data
        ctx = make_context({
            "tarifario": VALOR_TARIFARIO_FARMACIA,
            "responsable_cierra": FACTURADOR_NAME,
        })
        # The CUPS is NOT in nota_urgencias, but farmacia should skip before that check
        result = evaluator.evaluate({"operador": "cups_contratado"}, "OTHER_CUPS", None, ctx)
        assert result is True, "Farmacia should skip before urgencias check"

    def test_cap_check_before_entidad_check(self):
        """CAP ESS118 check before entidad_con_datos check."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"ESS118"}  # Known entity
        evaluator._pares_validos = {("ESS118", "CUPS_A")}  # Would be valid in pares
        evaluator._nota_cap_cups = {3: set()}  # Empty nota_cap[3]
        ctx = make_context({
            "codigo_entidad_cobrar": "ESS118",
            "numero_factura": "CAP-001",
        })
        # Even though (ESS118, CUPS_A) is in pares_validos, CAP check should fail first
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS_A", None, ctx)
        assert result is False, "CAP ESS118 check should fail before reaching pares_validos"

    def test_normal_pares_check_before_fev(self):
        """Normal pares_validos check happens before FEV exception."""
        evaluator = make_evaluator()
        evaluator._loaded = True
        evaluator._entidades_con_datos = {"EPS037"}
        evaluator._pares_validos = {("EPS037", "CUPS_X")}
        ctx = make_context({
            "codigo_entidad_cobrar": "EPS037",
            "numero_factura": "FEV-001",
        })
        # CUPS_X is in pares_validos, so should return True before reaching FEV
        result = evaluator.evaluate({"operador": "cups_contratado"}, "CUPS_X", None, ctx)
        assert result is True, "Normal pares check should succeed before FEV exception"
