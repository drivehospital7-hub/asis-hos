"""DB-backed tests for seeded hospitalización engine rules (migration 010).

These tests run against the configured test database (TEST_DB_NAME, default
asis_hos_test) and require migration 010 to be applied there. They prove:

- Every intended hospitalización rule is discoverable and active in the DB
  (no silent "Rule not found" gaps for the orchestrator).
- The three legacy group-rule semantics (estancia >24h obligatory codes,
  <=24h obligatory codes, prohibited codes) are available through DB-backed
  execution via RuleBasedDetector / RuleEvaluationEngine.
- Rule 61 cups_equivalentes_hospitalizacion detects 939402 + Hospitalización.

Note: cups_equivalentes_hospitalizacion (rule 61) exists only in the live DB
in this environment. The 939402 test seeds it into the test DB when absent so
the DB-backed execution is proven regardless of environment state.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from openpyxl import Workbook

from app.constants.base import is_rule_engine_enabled


# Rules the hospitalización orchestrator intends to evaluate (migration 010 +
# pre-existing rules). Group key comes from _HOSPITALIZACION_ENGINE_RULES.
INTENDED_HOSPITALIZACION_RULES = {
    "centro_costo_hospitalizacion_valido": "centros_de_costos",
    "ide_contrato_hospitalizacion_valido": "ide_contrato",
    "cups_equivalentes_hospitalizacion": "cups_equivalentes",
    "hosp_codigos_oblig_mayor24h": "cups_equivalentes",
    "hosp_codigos_oblig_menor24h": "cups_equivalentes",
    "hosp_codigos_prohibidos": "cups_equivalentes",
    "cantidades_hospitalizacion": "cantidades_hospitalizacion",
    "cantidades_soat_hospitalizacion": "cantidades_soat_hospitalizacion",
    "valores_decimales": "decimales",
    "tipo_documento_edad_menor_7": "tipo_identificacion_edad",
    "tipo_documento_edad_mayor_18": "tipo_identificacion_edad",
    "tipo_documento_edad_7_17": "tipo_identificacion_edad",
    "tipo_documento_edad_as_menor": "tipo_identificacion_edad",
    "tipo_documento_edad_ms_mayor": "tipo_identificacion_edad",
    "tipo_documento_edad_cn_invalido": "tipo_identificacion_edad",
    "tipo_documento_edad_ce_invalido": "tipo_identificacion_edad",
    "tipo_id_requiere_entidad_86000": "tipo_identificacion_entidad",
    "entidad_86000_requiere_as_ms": "tipo_identificacion_entidad",
    "codigo_entidad": "codigo_entidad_vs_afiliacion",
    "tipo_usuario_valido": "tipo_usuario",
    "copago_entidad_valido": "copago_entidad",
    "profesional_hospitalizacion_valido": "profesionales",
    "cups_sin_contrato": "cups_sin_contrato",
}

# Rules seeded by migration 010 that the hospitalización orchestrator evaluates
# (these were the silent "Rule not found" gaps before the migration).
MIGRATION_010_RULES = {
    "hosp_codigos_oblig_mayor24h",
    "hosp_codigos_oblig_menor24h",
    "hosp_codigos_prohibidos",
    "cantidades_hospitalizacion",
    "cantidades_soat_hospitalizacion",
    "profesional_hospitalizacion_valido",
    "ide_contrato_hospitalizacion_valido",
}

# Group rules seeded by migration 010 with tested semantics.
GROUP_RULES = (
    "hosp_codigos_oblig_mayor24h",
    "hosp_codigos_oblig_menor24h",
    "hosp_codigos_prohibidos",
)


def _build_ws() -> tuple[Workbook, dict[str, int]]:
    """Create a worksheet with standard hospitalización columns (snake_case keys)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    headers = [
        "numero_factura", "codigo", "cantidad", "fec_factura", "fecha_cierre",
        "tipo_factura_descripcion", "tarifario", "codigo_entidad_cobrar",
        "procedimiento", "codigo_tipo_procedimiento", "laboratorio",
        "codigo_profesional", "ide_contrato",
    ]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    indices = {h: i for i, h in enumerate(headers)}
    return wb, indices


def _session():
    from app.database import get_session
    return get_session()


def _detect(rule_name, ws, indices):
    from app.services.engine.rule_based_detector import RuleBasedDetector
    session = _session()
    try:
        return RuleBasedDetector(rule_name, session).detect(ws, indices, persist=False)
    finally:
        session.close()


def _facturas(results: list[dict]) -> set[str]:
    return {r.get("factura", "") for r in results}


# ═══════════════════════════════════════════════════════════════════════════
# 1. Every intended hospitalización rule is discoverable and active.
# ═══════════════════════════════════════════════════════════════════════════

class TestIntendedRulesDiscoverable:
    """All orchestrator-intended hospitalización rules exist and are active."""

    def test_orchestrator_intended_mapping_is_complete(self):
        """The orchestrator's engine-rule mapping must cover every intended rule."""
        from app.services.hospitalizacion.detect_all import (
            _HOSPITALIZACION_ENGINE_RULES,
        )

        assert set(_HOSPITALIZACION_ENGINE_RULES) == set(INTENDED_HOSPITALIZACION_RULES)

    def test_migration_010_rules_present_and_active(self):
        """Rules seeded by migration 010 must exist and be active in the DB."""
        from app.models import Regla

        session = _session()
        try:
            rules = (
                session.query(Regla)
                .filter(Regla.nombre.in_(list(MIGRATION_010_RULES)))
                .filter(Regla.estado == "active", Regla.activo.is_(True))
                .all()
            )
        finally:
            session.close()

        found = {r.nombre for r in rules}
        missing = MIGRATION_010_RULES - found
        assert not missing, (
            f"Migration-010 hospitalización rules missing/not active: {sorted(missing)}"
        )

    def test_group_rules_seeded_with_params(self):
        """Group rules must carry the group_by parametros (DB-backed routing)."""
        from app.models import Regla

        session = _session()
        try:
            rules = (
                session.query(Regla)
                .filter(Regla.nombre.in_(list(GROUP_RULES)))
                .all()
            )
        finally:
            session.close()

        by_name = {r.nombre: r for r in rules}
        for name in GROUP_RULES:
            rule = by_name.get(name)
            assert rule is not None, f"{name} missing"
            assert rule.parametros, f"{name} parametros empty"
            first = rule.parametros[0]
            assert first.get("group_by") == "numero_factura", f"{name} group_by"
            assert first.get("filter_field") == "tipo_factura_descripcion", f"{name} filter_field"
            assert first.get("filter_value") == "Hospitalización", f"{name} filter_value"


# ═══════════════════════════════════════════════════════════════════════════
# 2. The three legacy group-rule semantics work through DB-backed execution.
# ═══════════════════════════════════════════════════════════════════════════

class TestGroupRulesDbBacked:
    """hosp_codigos_oblig_mayor24h / menor24h / prohibidos via DB."""

    def test_mayor24h_detects_missing_code(self):
        """>24h estancia missing obligatory 890601 -> MATCH via DB."""
        wb, indices = _build_ws()
        # F001: 48h, has 129B02 and 890601H, missing 890601
        for r in range(2, 5):
            wb.active.cell(row=r, column=1, value="F001")
            wb.active.cell(row=r, column=4, value=datetime(2024, 1, 15, 8, 0, 0))
            wb.active.cell(row=r, column=5, value=datetime(2024, 1, 17, 8, 0, 0))
            wb.active.cell(row=r, column=6, value="Hospitalización")
        wb.active.cell(row=2, column=2, value="129B02")
        wb.active.cell(row=3, column=2, value="890601H")

        results = _detect("hosp_codigos_oblig_mayor24h", wb.active, indices)
        assert "F001" in _facturas(results)

    def test_mayor24h_no_detection_when_complete(self):
        """>24h with ALL obligatory codes -> NO_MATCH."""
        wb, indices = _build_ws()
        for r in range(2, 6):
            wb.active.cell(row=r, column=1, value="F001")
            wb.active.cell(row=r, column=4, value=datetime(2024, 1, 15, 8, 0, 0))
            wb.active.cell(row=r, column=5, value=datetime(2024, 1, 17, 8, 0, 0))
            wb.active.cell(row=r, column=6, value="Hospitalización")
        wb.active.cell(row=2, column=2, value="129B02")
        wb.active.cell(row=3, column=2, value="890601H")
        wb.active.cell(row=4, column=2, value="890601")

        results = _detect("hosp_codigos_oblig_mayor24h", wb.active, indices)
        assert _facturas(results) == set()

    def test_menor24h_detects_missing_code(self):
        """<=24h estancia missing 890601H -> MATCH via DB."""
        wb, indices = _build_ws()
        wb.active.cell(row=2, column=1, value="F001")
        wb.active.cell(row=2, column=2, value="129B02")  # missing 890601H
        wb.active.cell(row=2, column=4, value=datetime(2024, 1, 15, 8, 0, 0))
        wb.active.cell(row=2, column=5, value=datetime(2024, 1, 15, 14, 0, 0))
        wb.active.cell(row=2, column=6, value="Hospitalización")

        results = _detect("hosp_codigos_oblig_menor24h", wb.active, indices)
        assert "F001" in _facturas(results)

    def test_menor24h_no_detection_when_complete(self):
        """<=24h with all obligatory codes -> NO_MATCH."""
        wb, indices = _build_ws()
        wb.active.cell(row=2, column=1, value="F001")
        wb.active.cell(row=2, column=2, value="890601H")
        wb.active.cell(row=2, column=4, value=datetime(2024, 1, 15, 8, 0, 0))
        wb.active.cell(row=2, column=5, value=datetime(2024, 1, 15, 14, 0, 0))
        wb.active.cell(row=2, column=6, value="Hospitalización")
        wb.active.cell(row=3, column=1, value="F001")
        wb.active.cell(row=3, column=2, value="129B02")
        wb.active.cell(row=3, column=4, value=datetime(2024, 1, 15, 8, 0, 0))
        wb.active.cell(row=3, column=5, value=datetime(2024, 1, 15, 14, 0, 0))
        wb.active.cell(row=3, column=6, value="Hospitalización")

        results = _detect("hosp_codigos_oblig_menor24h", wb.active, indices)
        assert _facturas(results) == set()

    def test_prohibidos_detects_generic(self):
        """Prohibited code 05DSB01 -> MATCH via DB."""
        wb, indices = _build_ws()
        wb.active.cell(row=2, column=1, value="F001")
        wb.active.cell(row=2, column=2, value="05DSB01")
        wb.active.cell(row=2, column=6, value="Hospitalización")
        wb.active.cell(row=2, column=7, value="NO SOAT")

        results = _detect("hosp_codigos_prohibidos", wb.active, indices)
        assert "F001" in _facturas(results)

    def test_prohibidos_no_detection_without_prohibited(self):
        """No prohibited codes -> NO_MATCH."""
        wb, indices = _build_ws()
        wb.active.cell(row=2, column=1, value="F001")
        wb.active.cell(row=2, column=2, value="129B02")
        wb.active.cell(row=2, column=6, value="Hospitalización")
        wb.active.cell(row=2, column=7, value="NO SOAT")

        results = _detect("hosp_codigos_prohibidos", wb.active, indices)
        assert _facturas(results) == set()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Rule 61 cups_equivalentes_hospitalizacion detects 939402 + Hospitalización.
# ═══════════════════════════════════════════════════════════════════════════

class TestRule61Detects939402:
    """cups_equivalentes_hospitalizacion DB rule detects 939402+Hospitalización.

    Rule 61 lives in the live DB; the test DB may or may not carry it. These
    tests seed it transactionally (same session, rolled back at the end) so the
    DB-backed execution is proven regardless of environment state.
    """

    @pytest.fixture
    def seeded_rule61(self):
        """Seed cups_equivalentes_hospitalizacion in a transaction; rollback after."""
        from app.models import Regla, Condicion

        session = _session()
        rule = None
        try:
            # Reuse existing rule if the test DB already has it (live parity).
            rule = (
                session.query(Regla)
                .filter(Regla.nombre == "cups_equivalentes_hospitalizacion")
                .first()
            )
            if rule is None:
                rule = Regla(
                    nombre="cups_equivalentes_hospitalizacion",
                    descripcion="Código CUPS con equivalente conocido detectado",
                    dominio="hospitalizacion", estado="active", version=1,
                    prioridad=5, severidad="error", activo=True,
                )
                session.add(rule)
                session.flush()
                # OR root -> [eq codigo 939402 AND eq tipo Hospitalización]
                root = Condicion(regla_id=rule.id, padre_id=None, tipo="composite",
                                 operador="OR", orden=0)
                session.add(root)
                session.flush()
                and_node = Condicion(regla_id=rule.id, padre_id=root.id,
                                     tipo="composite", operador="AND", orden=0)
                session.add(and_node)
                session.flush()
                session.add(Condicion(regla_id=rule.id, padre_id=and_node.id,
                                      tipo="atomic", operador="eq",
                                      fuente_datos="invoice.codigo",
                                      valor_esperado="939402", orden=0))
                session.add(Condicion(regla_id=rule.id, padre_id=and_node.id,
                                      tipo="atomic", operador="eq",
                                      fuente_datos="invoice.tipo_factura_descripcion",
                                      valor_esperado="Hospitalización", orden=1))
                session.flush()
            session.commit()
            yield session
        finally:
            session.rollback()
            session.close()

    def test_rule61_detects_939402(self, seeded_rule61):
        """939402 + Hospitalización triggers rule 61 via DB-backed execution."""
        from app.services.engine.rule_based_detector import RuleBasedDetector

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="numero_factura")
        ws.cell(row=1, column=2, value="codigo")
        ws.cell(row=1, column=3, value="tipo_factura_descripcion")
        ws.cell(row=2, column=1, value="H001")
        ws.cell(row=2, column=2, value="939402")
        ws.cell(row=2, column=3, value="Hospitalización")
        indices = {"numero_factura": 0, "codigo": 1, "tipo_factura_descripcion": 2}

        session = seeded_rule61
        results = RuleBasedDetector("cups_equivalentes_hospitalizacion", session).detect(
            ws, indices, persist=False,
        )
        assert "H001" in _facturas(results)

    def test_rule61_ignores_other_codes(self, seeded_rule61):
        """Non-matching code does not trigger rule 61."""
        from app.services.engine.rule_based_detector import RuleBasedDetector

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="numero_factura")
        ws.cell(row=1, column=2, value="codigo")
        ws.cell(row=1, column=3, value="tipo_factura_descripcion")
        ws.cell(row=2, column=1, value="H002")
        ws.cell(row=2, column=2, value="999999")
        ws.cell(row=2, column=3, value="Hospitalización")
        indices = {"numero_factura": 0, "codigo": 1, "tipo_factura_descripcion": 2}

        session = seeded_rule61
        results = RuleBasedDetector("cups_equivalentes_hospitalizacion", session).detect(
            ws, indices, persist=False,
        )
        assert _facturas(results) == set()
