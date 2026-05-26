"""Tests for app/services/transversales/centro_costo_rules.py — shared centro_costo rules.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

import pytest

from app.services.transversales.centro_costo_rules import apply_common_centro_costo_rules


class TestApplyCommonCentroCostoRules:
    """Shared centro_costo rules: 1, 1-REVERSE, 2, 2-REVERSE, 3, 3-REVERSE,
    4, 4-REVERSE, 8, 9, 9-REVERSE, CENTRO_INVALIDO."""

    def test_centro_invalido_rule(self):
        """Centro costo not in valid list → error with prioridad 1."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_INEXISTENTE",
            codigo_str="",
            codigo_excluir="",
            laboratorio_str="",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
            centros_validos=frozenset({"CENTRO_A", "CENTRO_B"}),
        )
        assert len(errors) >= 1
        e = errors[0]
        assert e["centro_deberia"] == "Centro de costo no válido para Urgencias"
        assert e["prioridad"] == 1

    def test_centro_valido_no_error(self):
        """Valid centro costo produces no CENTRO_INVALIDO error."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="",
            codigo_excluir="",
            laboratorio_str="",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
            centros_validos=frozenset({"CENTRO_A", "CENTRO_B"}),
        )
        # No centro_invalido error (may have other rules trigger, but not this one)
        centro_invalido = [e for e in errors if e.get("regla") == "CENTRO_INVALIDO"]
        assert centro_invalido == []

    def test_regla9_tarifario_farmacia(self):
        """Tarifario='Suminstros, Medicamentos' → centro debe ser FARMACIA."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="",
            codigo_excluir="",
            laboratorio_str="",
            tarifario_str="Suminstros, Medicamentos",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        regla9 = [e for e in errors if e.get("regla") == "REGLA9"]
        assert len(regla9) == 1
        assert regla9[0]["centro_deberia"] is not None

    def test_regla9_tarifario_farmacia_centro_correcto_no_error(self):
        """Tarifario=farmacia with FARMACIA centro → no error."""
        from app.constants import CENTRO_COSTO_FARMACIA, VALOR_TARIFARIO_FARMACIA
        errors = apply_common_centro_costo_rules(
            centro_costo_str=CENTRO_COSTO_FARMACIA,
            codigo_str="",
            codigo_excluir="",
            laboratorio_str="",
            tarifario_str=VALOR_TARIFARIO_FARMACIA,
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        regla9 = [e for e in errors if e.get("regla") == "REGLA9"]
        assert regla9 == []

    def test_regla1_codigo_02_lab_no(self):
        """Código=02 + Lab=No + not exceptuado → centro APOYO DIAGNOSTICO."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="02",
            codigo_excluir="12345",
            laboratorio_str="No",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        regla1 = [e for e in errors if e.get("regla", "") == ""  # REGLA1 has no explicit regla key
                   and e.get("centro_deberia") is not None]
        assert len(regla1) >= 1

    def test_regla1_exceptuado_no_error(self):
        """Código in CODIGOS_EXCEPTUADOS → no REGLA1 error."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="02",
            codigo_excluir="39156",  # known exceptuado
            laboratorio_str="No",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        # No REGLA1 error triggered because exceptuado
        regla1_errors = [
            e for e in errors
            if "REGLA1" not in str(e.get("regla", ""))
            and e.get("centro_deberia") == "730 APOYO DIAGNOSTICO"
        ]
        assert regla1_errors == []

    def test_empty_centro_costo_skips_all(self):
        """Empty centro_costo skipped for all rules."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="",
            codigo_str="02",
            codigo_excluir="12345",
            laboratorio_str="No",
            tarifario_str="Suminstros, Medicamentos",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        assert errors == []

    def test_regla2_codigo_14_traslados(self):
        """Código=14 → centro debe ser TRASLADOS."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="14",
            codigo_excluir="",
            laboratorio_str="",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        # REGLA2: código 14, centro != TRASLADOS
        traslados = [e for e in errors if "TRASLADOS" in str(e.get("centro_deberia", ""))]
        assert len(traslados) >= 1

    def test_regla8_codigo_hosp_estancia(self):
        """Código 890601H or 39133 → centro HOSPITALIZACION ESTANCIA."""
        errors = apply_common_centro_costo_rules(
            centro_costo_str="CENTRO_A",
            codigo_str="",
            codigo_excluir="890601H",
            laboratorio_str="",
            tarifario_str="",
            codigo_entidad_str="",
            factura_str="FAC-001",
            proc_str="Test Proc",
        )
        regla8 = [e for e in errors if "ESTANCIA GENERAL" in str(e.get("centro_deberia", ""))]
        assert len(regla8) >= 1
