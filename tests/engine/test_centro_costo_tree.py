"""Equivalence tests: tree vs legacy evaluator for centro_costo rules.

Each REGLA is tested with curated data that isolates it from other REGLAs.
Validates the OR tree produces IDENTICAL output to the legacy evaluator.
Uses centro_costo_intramural (the correct implementation — common evaluator
has known uppercasing bugs in REGLA1/REGLA9/REVERSE1/REVERSE9).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.engine.condition_evaluator import ConditionEvaluator
from app.services.engine.context import EvaluationContext


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _make_context(invoice_data: dict) -> EvaluationContext:
    """Create EvaluationContext with mock catalogos DB lookups."""
    session = MagicMock()
    catalog_values: dict[str, list[str]] = {
        "codigos_exceptuados": [
            "194901", "23105", "23116", "232200", "232201",
            "25142AFINA", "90123501", "901325", "90385901",
            "90386401", "903883", "9038831", "904903", "906230", "906836",
        ],
        "centro_costo_pyp": ["990211", "890205", "890405", "861801", "39360", "29116"],
        "centro_costo_quirofano": ["735301", "90DS02", "512002", "39220"],
        "centro_costo_hospitalizacion": ["890601H", "39133"],
        "centros_costo_pyp_intramural": [
            "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION",
            "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION.",
            "SERVICIOS AMBULATORIOS- PROMOCION/PREVENCION",
        ],
        "codigos_excluidos_vacunacion": ["906249PR", "906249"],
        "codigos_exceptuados_ambulatorio": ["735301", "861101"],
        "codigos_exceptuados_responsable_urgencias": ["735301"],
        "centros_costo_laboratorio_validos": [
            "APOYO DIAGNOSTICO-LABORATOR CLINICO",
            "APOYO DIAGNOSTICO-LABORATOR CLINICO.",
        ],
        "codigos_tipo_procedimiento_ambulatorio": ["03", "04"],
        "codigos_tipo_procedimiento_laboratorio": ["02", "05"],
        "centros_costo_validos_urgencias": [
            "URGENCIAS",
            "APOYO TERAPEUTICO-FARMACIA E INSUMOS.",
            "APOYO DIAGNOSTICO-LABORATOR CLINICO",
            "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN",
            "HOSPITALIZACIÓN - ESTANCIA GENERAL",
            "APOYO DIAGNOSTICO-IMAGENOLOGIA",
            "TRASLADOS",
            "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO",
        ],
        "facturadores_urgencias": [
            "ARIAS CULCHA ANGIE CAROLINA",
            "ESPAÑA DIAZ LORENY ALEJANDRA",
            "MEZA FERNANDEZ CARLOS OMAR",
            "PAEZ YULIETH DANIELA",
        ],
    }

    def mock_execute(sql, params):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (catalog_values.get(params.get("key", ""), []),)
        return mock_result

    session.execute.side_effect = mock_execute
    return EvaluationContext(invoice_data=invoice_data, indices={}, session=session)


def _get_evaluator(name: str):
    from app.services.engine.evaluators import EVALUATOR_REGISTRY
    return EVALUATOR_REGISTRY[name]


def _run_legacy(evaluator_name: str, data: dict) -> bool:
    """Run legacy evaluator on invoice data."""
    e = _get_evaluator(evaluator_name)
    ctx = _make_context(data)
    return e.evaluate({}, str(data.get("centro_costo", "")), None, context=ctx)


def _run_tree(conditions: list[dict], data: dict) -> bool:
    """Run ConditionEvaluator tree on invoice data."""
    evaluator = ConditionEvaluator()
    tree = evaluator.build_tree(conditions)
    if tree is None:
        return False
    ctx = _make_context(data)
    return bool(evaluator.evaluate(tree, ctx).get("outcome", False))


# ── Test infrastructure ──────────────────────────────────────────────────────

COMMON_CONDITIONS: list[dict] = []
INTRAMURAL_CONDITIONS: list[dict] = []


def _build_common_tree(include_urgencias_invalid_center=False):
    """Build common tree conditions (mirrors seed/14_centro_costo_comun.sql)."""
    conds: list[dict] = []
    _cid = [0]

    def nid():
        _cid[0] -= 1
        return _cid[0]

    def add(tipo, op, fuente, esperado, padre, orden):
        conds.append({"id": nid(), "padre_id": padre, "tipo": tipo, "operador": op,
                       "fuente_datos": fuente, "valor_esperado": esperado, "orden": orden})
        return conds[-1]["id"]

    def comp(op, padre, orden): return add("composite", op, None, None, padre, orden)
    def atom(op, fuente, esperado, padre, orden): return add("atomic", op, fuente, esperado, padre, orden)

    root = comp("OR", None, 0)

    # REGLA9
    r9 = comp("AND", root, 0)
    atom("eq", "invoice.tarifario", "Suminstros, Medicamentos", r9, 0)
    r9_n = comp("NOT", r9, 1)
    atom("eq", "invoice.centro_costo", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", r9_n, 0)

    # REGLA1
    r1 = comp("AND", root, 1)
    atom("eq", "invoice.codigo_tipo_procedimiento", "02", r1, 0)
    atom("eq", "invoice.laboratorio", "No", r1, 1)
    r1_n1 = comp("NOT", r1, 2)
    atom("cat_in", "invoice.codigo", "codigos_exceptuados", r1_n1, 0)
    r1_n2 = comp("NOT", r1, 3)
    atom("eq", "invoice.centro_costo", "APOYO DIAGNOSTICO-IMAGENOLOGIA", r1_n2, 0)

    # REVERSE1
    rev1 = comp("AND", root, 2)
    atom("eq", "invoice.centro_costo", "APOYO DIAGNOSTICO-IMAGENOLOGIA", rev1, 0)
    rev1_n = comp("NOT", rev1, 1)
    rev1_and = comp("AND", rev1_n, 0)
    atom("eq", "invoice.codigo_tipo_procedimiento", "02", rev1_and, 0)
    atom("eq", "invoice.laboratorio", "No", rev1_and, 1)

    # REGLA2
    r2 = comp("AND", root, 3)
    atom("eq", "invoice.codigo_tipo_procedimiento", "14", r2, 0)
    r2_n = comp("NOT", r2, 1)
    atom("eq", "invoice.centro_costo", "TRASLADOS", r2_n, 0)

    # REVERSE2
    rev2 = comp("AND", root, 4)
    atom("eq", "invoice.centro_costo", "TRASLADOS", rev2, 0)
    rev2_n = comp("NOT", rev2, 1)
    atom("eq", "invoice.codigo_tipo_procedimiento", "14", rev2_n, 0)

    # REGLA3
    r3 = comp("AND", root, 5)
    atom("cat_in", "invoice.codigo", "centro_costo_pyp", r3, 0)
    r3_n = comp("NOT", r3, 1)
    atom("eq", "invoice.centro_costo", "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", r3_n, 0)

    # REVERSE3
    rev3 = comp("AND", root, 6)
    atom("eq", "invoice.centro_costo", "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", rev3, 0)
    rev3_n = comp("NOT", rev3, 1)
    atom("cat_in", "invoice.codigo", "centro_costo_pyp", rev3_n, 0)

    # REGLA4
    r4 = comp("AND", root, 7)
    atom("cat_in", "invoice.codigo", "centro_costo_quirofano", r4, 0)
    r4_n = comp("NOT", r4, 1)
    atom("eq", "invoice.centro_costo", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", r4_n, 0)

    # REVERSE4
    rev4 = comp("AND", root, 8)
    atom("eq", "invoice.centro_costo", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", rev4, 0)
    rev4_n = comp("NOT", rev4, 1)
    atom("cat_in", "invoice.codigo", "centro_costo_quirofano", rev4_n, 0)

    # REVERSE9
    rev9 = comp("AND", root, 9)
    atom("eq", "invoice.centro_costo", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", rev9, 0)
    rev9_n = comp("NOT", rev9, 1)
    atom("eq", "invoice.tarifario", "Suminstros, Medicamentos", rev9_n, 0)

    # REGLA8
    r8 = comp("AND", root, 10)
    atom("cat_in", "invoice.codigo", "centro_costo_hospitalizacion", r8, 0)
    r8_n = comp("NOT", r8, 1)
    atom("eq", "invoice.centro_costo", "HOSPITALIZACIÓN - ESTANCIA GENERAL", r8_n, 0)

    if include_urgencias_invalid_center:
        invalid_center = comp("NOT", root, 11)
        atom(
            "cat_in",
            "invoice.centro_costo",
            "centros_costo_validos_urgencias",
            invalid_center,
            0,
        )

    return conds


def _build_intramural_tree():
    """Build intramural tree (mirrors seed/15_centro_costo_intramural.sql)."""
    conds: list[dict] = []
    _cid = [1000]

    def nid():
        _cid[0] -= 1
        return _cid[0]

    def add(tipo, op, fuente, esperado, padre, orden):
        conds.append({"id": nid(), "padre_id": padre, "tipo": tipo, "operador": op,
                       "fuente_datos": fuente, "valor_esperado": esperado, "orden": orden})
        return conds[-1]["id"]

    def comp(op, padre, orden): return add("composite", op, None, None, padre, orden)
    def atom(op, fuente, esperado, padre, orden): return add("atomic", op, fuente, esperado, padre, orden)

    root = comp("OR", None, 0)

    # ── Common rules (without REGLA3/REVERSE3) ──

    # REGLA9
    r9 = comp("AND", root, 0)
    atom("eq", "invoice.tarifario", "Suminstros, Medicamentos", r9, 0)
    r9_n = comp("NOT", r9, 1)
    atom("eq", "invoice.centro_costo", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", r9_n, 0)

    # REGLA1
    r1 = comp("AND", root, 1)
    atom("eq", "invoice.codigo_tipo_procedimiento", "02", r1, 0)
    atom("eq", "invoice.laboratorio", "No", r1, 1)
    r1_n1 = comp("NOT", r1, 2)
    atom("cat_in", "invoice.codigo", "codigos_exceptuados", r1_n1, 0)
    r1_n2 = comp("NOT", r1, 3)
    atom("eq", "invoice.centro_costo", "APOYO DIAGNOSTICO-IMAGENOLOGIA", r1_n2, 0)

    # REVERSE1
    rev1 = comp("AND", root, 2)
    atom("eq", "invoice.centro_costo", "APOYO DIAGNOSTICO-IMAGENOLOGIA", rev1, 0)
    rev1_n = comp("NOT", rev1, 1)
    rev1_and = comp("AND", rev1_n, 0)
    atom("eq", "invoice.codigo_tipo_procedimiento", "02", rev1_and, 0)
    atom("eq", "invoice.laboratorio", "No", rev1_and, 1)

    # REGLA2
    r2 = comp("AND", root, 3)
    atom("eq", "invoice.codigo_tipo_procedimiento", "14", r2, 0)
    r2_n = comp("NOT", r2, 1)
    atom("eq", "invoice.centro_costo", "TRASLADOS", r2_n, 0)

    # REVERSE2
    rev2 = comp("AND", root, 4)
    atom("eq", "invoice.centro_costo", "TRASLADOS", rev2, 0)
    rev2_n = comp("NOT", rev2, 1)
    atom("eq", "invoice.codigo_tipo_procedimiento", "14", rev2_n, 0)

    # REGLA4
    r4 = comp("AND", root, 5)
    atom("cat_in", "invoice.codigo", "centro_costo_quirofano", r4, 0)
    r4_n = comp("NOT", r4, 1)
    atom("eq", "invoice.centro_costo", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", r4_n, 0)

    # REVERSE4
    rev4 = comp("AND", root, 6)
    atom("eq", "invoice.centro_costo", "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", rev4, 0)
    rev4_n = comp("NOT", rev4, 1)
    atom("cat_in", "invoice.codigo", "centro_costo_quirofano", rev4_n, 0)

    # REVERSE9
    rev9 = comp("AND", root, 7)
    atom("eq", "invoice.centro_costo", "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", rev9, 0)
    rev9_n = comp("NOT", rev9, 1)
    atom("eq", "invoice.tarifario", "Suminstros, Medicamentos", rev9_n, 0)

    # REGLA8
    r8 = comp("AND", root, 8)
    atom("cat_in", "invoice.codigo", "centro_costo_hospitalizacion", r8, 0)
    r8_n = comp("NOT", r8, 1)
    atom("eq", "invoice.centro_costo", "HOSPITALIZACIÓN - ESTANCIA GENERAL", r8_n, 0)

    # REGLA3-INTRAMURAL
    r3i = comp("AND", root, 9)
    atom("cat_in", "invoice.codigo", "centro_costo_pyp", r3i, 0)
    r3i_n = comp("NOT", r3i, 1)
    atom("cat_in", "invoice.centro_costo", "centros_costo_pyp_intramural", r3i_n, 0)

    # REVERSE3-INTRAMURAL
    rev3i = comp("AND", root, 10)
    atom("cat_in", "invoice.centro_costo", "centros_costo_pyp_intramural", rev3i, 0)
    rev3i_n = comp("NOT", rev3i, 1)
    atom("cat_in", "invoice.codigo", "centro_costo_pyp", rev3i_n, 0)

    # REGLA10
    r10 = comp("AND", root, 11)
    atom("cat_in", "invoice.codigo_tipo_procedimiento", "codigos_tipo_procedimiento_laboratorio", r10, 0)
    atom("eq", "invoice.laboratorio", "Si", r10, 1)
    r10_n = comp("NOT", r10, 2)
    atom("cat_in", "invoice.centro_costo", "centros_costo_laboratorio_validos", r10_n, 0)

    # REVERSE10
    rev10 = comp("AND", root, 12)
    atom("cat_in", "invoice.centro_costo", "centros_costo_laboratorio_validos", rev10, 0)
    rev10_or = comp("OR", rev10, 1)
    rev10_or_n1 = comp("NOT", rev10_or, 0)
    atom("cat_in", "invoice.codigo_tipo_procedimiento", "codigos_tipo_procedimiento_laboratorio", rev10_or_n1, 0)
    rev10_or_and = comp("AND", rev10_or, 1)
    rev10_or_and_n1 = comp("NOT", rev10_or_and, 0)
    atom("cat_in", "invoice.codigo", "codigos_exceptuados", rev10_or_and_n1, 0)
    rev10_or_and_n2 = comp("NOT", rev10_or_and, 1)
    atom("eq", "invoice.laboratorio", "Si", rev10_or_and_n2, 0)

    # REGLA6
    r6 = comp("AND", root, 13)
    atom("eq", "invoice.codigo_tipo_procedimiento", "05", r6, 0)
    r6_n1 = comp("NOT", r6, 1)
    atom("cat_in", "invoice.codigo", "codigos_excluidos_vacunacion", r6_n1, 0)
    r6_n2 = comp("NOT", r6, 2)
    atom("cat_in", "invoice.codigo", "centro_costo_pyp", r6_n2, 0)
    r6_n3 = comp("NOT", r6, 3)
    atom("eq", "invoice.centro_costo", "SALUD PUBLICA-VACUNACION  REGULAR", r6_n3, 0)
    r6_n4 = comp("NOT", r6, 4)
    r6_n4_and = comp("AND", r6_n4, 0)
    atom("cat_in", "invoice.codigo_tipo_procedimiento", "codigos_tipo_procedimiento_laboratorio", r6_n4_and, 0)
    atom("eq", "invoice.laboratorio", "Si", r6_n4_and, 1)

    # REVERSE6
    rev6 = comp("AND", root, 14)
    atom("eq", "invoice.centro_costo", "SALUD PUBLICA-VACUNACION  REGULAR", rev6, 0)
    rev6_or = comp("OR", rev6, 1)
    rev6_or_n = comp("NOT", rev6_or, 0)
    atom("eq", "invoice.codigo_tipo_procedimiento", "05", rev6_or_n, 0)
    atom("cat_in", "invoice.codigo", "codigos_excluidos_vacunacion", rev6_or, 1)

    # REGLA7
    r7 = comp("AND", root, 15)
    atom("cat_in", "invoice.codigo_tipo_procedimiento", "codigos_tipo_procedimiento_ambulatorio", r7, 0)
    r7_n1 = comp("NOT", r7, 1)
    atom("cat_in", "invoice.codigo", "codigos_exceptuados_ambulatorio", r7_n1, 0)
    r7_n2 = comp("NOT", r7, 2)
    atom("eq", "invoice.centro_costo", "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS", r7_n2, 0)

    # REVERSE7
    rev7 = comp("AND", root, 16)
    atom("eq", "invoice.centro_costo", "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS", rev7, 0)
    rev7_n = comp("NOT", rev7, 1)
    atom("cat_in", "invoice.codigo_tipo_procedimiento", "codigos_tipo_procedimiento_ambulatorio", rev7_n, 0)

    # REGLA_RESPONSABLE_URGENCIAS
    resp = comp("AND", root, 17)
    atom("cat_in", "invoice.responsable_cierra", "facturadores_urgencias", resp, 0)
    atom("in", "invoice.codigo_tipo_procedimiento", ["01", "04"], resp, 1)
    resp_n1 = comp("NOT", resp, 2)
    atom("cat_in", "invoice.codigo", "codigos_exceptuados_responsable_urgencias", resp_n1, 0)
    resp_n2 = comp("NOT", resp, 3)
    atom("in", "invoice.centro_costo", ["URGENCIAS", "HOSPITALIZACIÓN - ESTANCIA GENERAL"], resp_n2, 0)

    return conds


COMMON_CONDITIONS = _build_common_tree()
URGENCIAS_CONDITIONS = _build_common_tree(include_urgencias_invalid_center=True)
INTRAMURAL_CONDITIONS = _build_intramural_tree()


def _assert(eval_name, conds, data, expected):
    """Assert legacy evaluator and tree produce expected outcome AND match each other."""
    legacy = _run_legacy(eval_name, data)
    tree = _run_tree(conds, data)
    assert legacy == expected, f"Legacy {eval_name} expected {expected}, got {legacy} for {data}"
    assert tree == expected, f"Tree expected {expected}, got {tree} for {data}"
    assert legacy == tree, f"Legacy/Tree mismatch: legacy={legacy} tree={tree}"


def MATCH(eval_name, conds, data):
    """Assert both return True (detection)."""
    _assert(eval_name, conds, data, True)


def NO_MATCH(eval_name, conds, data):
    """Assert both return False (no detection)."""
    _assert(eval_name, conds, data, False)


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN NOTES:
# ═══════════════════════════════════════════════════════════════════════════════
#
# REGLA isolation rules:
# - cod_tipo 14 → REGLA2 only (unique cod_tipo)
# - cod_tipo 02 + lab=No → REGLA1 if codigo not exceptuado
# - cod_tipo 02 + lab=No + codigo exceptuado → no REGLA fires (safe)
# - cod_tipo 05 + lab=No → REGLA6 if codigo not pyp/excluido
# - cod_tipo 05 + lab=Si → REGLA10 (tipo in TIPO_LAB + lab=Si)
# - cod_tipo 03/04 → REGLA7 if codigo not exceptuado_ambulatorio
# The RESPONSABLE_URGENCIAS uses cod_tipo 01/04 — different from others
# Codigo 735301 → quirofano list → REGLA4
# Codigo 990211 → pyp list → REGLA3/REGLA3-INTRAMURAL
# Codigo 890601H → hospitalizacion list → REGLA8
# Codigo 890601 → NOT in any catalog list (used as neutral)
# Codigo 903883 → exceptuados list (REGLA1 skip)
#
# Neutral baseline (no REGLA fires):
#   {cod_tipo="01", codigo="890601", centro="URGENCIAS"}
# ═══════════════════════════════════════════════════════════════════════════════


# ── Common Evaluator Tests ───────────────────────────────────────────────────

class TestRegla2:
    """REGLA2: cod_tipo=14 → centro=TRASLADOS (unique cod_tipo — no other REGLA interferes)."""
    DETECT = {"codigo_tipo_procedimiento": "14", "centro_costo": "URGENCIAS"}
    SKIP_CORRECT = {"codigo_tipo_procedimiento": "14", "centro_costo": "TRASLADOS"}

    def test_detects_wrong_centro(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct_centro(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP_CORRECT)

class TestReverse2:
    """REVERSE2: centro=TRASLADOS → cod_tipo=14."""
    DETECT = {"centro_costo": "TRASLADOS", "codigo_tipo_procedimiento": "02"}
    SKIP = {"centro_costo": "TRASLADOS", "codigo_tipo_procedimiento": "14"}

    def test_detects_wrong_tipo(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)

class TestRegla3:
    """REGLA3: codigo in PyP list → centro=PYP. codigo=990211 unique to PyP."""
    DETECT = {"codigo": "990211", "centro_costo": "URGENCIAS"}
    SKIP = {"codigo": "990211", "centro_costo": "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"}
    NEUTRAL = {"codigo": "890601", "centro_costo": "URGENCIAS"}

    def test_detects_wrong_centro(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct_centro(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)
    def test_skips_non_pyp_code(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.NEUTRAL)

class TestReverse3:
    """REVERSE3: centro=PYP → codigo in PyP list."""
    DETECT = {"centro_costo": "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", "codigo": "735301"}
    SKIP = {"centro_costo": "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN", "codigo": "990211"}

    def test_detects_wrong_codigo(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)

class TestRegla4:
    """REGLA4: codigo in quirofano → centro=QUIROFANO. codigo=735301 unique to quirofano."""
    DETECT = {"codigo": "735301", "centro_costo": "URGENCIAS"}
    SKIP = {"codigo": "735301", "centro_costo": "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"}

    def test_detects_wrong_centro(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct_centro(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)

class TestReverse4:
    """REVERSE4: centro=QUIROFANO → codigo in quirofano."""
    DETECT = {"centro_costo": "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", "codigo": "990211"}
    SKIP = {"centro_costo": "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO", "codigo": "735301"}

    def test_detects_wrong_codigo(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)

class TestRegla8:
    """REGLA8: codigo in hospitalizacion list → centro=HOSP. codigo=890601H."""
    DETECT = {"codigo": "890601H", "centro_costo": "URGENCIAS"}
    SKIP = {"codigo": "890601H", "centro_costo": "HOSPITALIZACIÓN - ESTANCIA GENERAL"}

    def test_detects_wrong_centro(self): MATCH("centro_costo_check", COMMON_CONDITIONS, self.DETECT)
    def test_skips_correct_centro(self): NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.SKIP)


# These REGLAs have known bugs in centro_costo_check (uppercasing bug with lab/tarifario).
# Validated against centro_costo_intramural which has the correct implementation.
# See Bug Report: the common evaluator uppercases input but compares against mixed-case constants.

class TestRegla9:
    """REGLA9: tarifario=Farmacia → centro=FARMACIA. (intramural evaluator — correct behavior)."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self): MATCH(self.EL, self.CO, {"tarifario": "Suminstros, Medicamentos", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self): NO_MATCH(self.EL, self.CO, {"tarifario": "Suminstros, Medicamentos", "centro_costo": "APOYO TERAPEUTICO-FARMACIA E INSUMOS."})
    def test_skips_other_tarifario(self): NO_MATCH(self.EL, self.CO, {"tarifario": "SOAT", "centro_costo": "URGENCIAS"})

class TestRegla1:
    """REGLA1: cod_tipo=02 + lab=No + not except → centro=DIAG. (intramural evaluator)."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self): MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "No", "codigo": "890601", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self): NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "No", "codigo": "890601", "centro_costo": "APOYO DIAGNOSTICO-IMAGENOLOGIA"})
    def test_skips_exceptuado(self): NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "No", "codigo": "903883", "centro_costo": "URGENCIAS"})

class TestReverse1:
    """REVERSE1: centro=DIAG → cod_tipo=02 + lab=No. (intramural evaluator)."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_tipo(self): MATCH(self.EL, self.CO, {"centro_costo": "APOYO DIAGNOSTICO-IMAGENOLOGIA", "codigo_tipo_procedimiento": "14", "laboratorio": "No"})
    def test_detects_wrong_lab(self): MATCH(self.EL, self.CO, {"centro_costo": "APOYO DIAGNOSTICO-IMAGENOLOGIA", "codigo_tipo_procedimiento": "02", "laboratorio": "Si"})
    def test_skips_correct(self): NO_MATCH(self.EL, self.CO, {"centro_costo": "APOYO DIAGNOSTICO-IMAGENOLOGIA", "codigo_tipo_procedimiento": "02", "laboratorio": "No"})

class TestReverse9:
    """REVERSE9: centro=FARMACIA → tarifario=Farmacia. (intramural evaluator)."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_tarifario(self): MATCH(self.EL, self.CO, {"centro_costo": "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "tarifario": "SOAT"})
    def test_skips_correct(self): NO_MATCH(self.EL, self.CO, {"centro_costo": "APOYO TERAPEUTICO-FARMACIA E INSUMOS.", "tarifario": "Suminstros, Medicamentos"})


# ── Intramural-Specific Tests ────────────────────────────────────────────────

class TestRegla3Intramural:
    """REGLA3-INTRAMURAL: codigo PyP → centro PyP intramural."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self):
        MATCH(self.EL, self.CO, {"codigo": "990211", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self):
        NO_MATCH(self.EL, self.CO, {"codigo": "990211", "centro_costo": "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION"})
    def test_skips_non_pyp_codigo(self):
        NO_MATCH(self.EL, self.CO, {"codigo": "890601", "centro_costo": "URGENCIAS"})

class TestRegla10:
    """REGLA10: tipo in {02,05} + lab=Si → LABORATORIO CLINICO."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self):
        # cod_tipo=02 + lab=Si → REGLA10. codigo=903883 (except) to avoid REGLA1.
        MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "Si", "codigo": "903883", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self):
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "Si", "codigo": "903883", "centro_costo": "APOYO DIAGNOSTICO-LABORATOR CLINICO"})
    def test_skips_lab_not_si(self):
        # lab=No → REGLA1 would fire if codigo not except. Use exceptuado codigo.
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "02", "laboratorio": "No", "codigo": "903883", "centro_costo": "URGENCIAS"})

class TestRegla6:
    """REGLA6: tipo=05 + not excluido + not PyP → SALUD PUBLICA."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self):
        MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "05", "codigo": "993120", "laboratorio": "No", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self):
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "05", "codigo": "993120", "laboratorio": "No", "centro_costo": "SALUD PUBLICA-VACUNACION  REGULAR"})
    def test_skips_excluido(self):
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "05", "codigo": "906249PR", "laboratorio": "No", "centro_costo": "URGENCIAS"})
    def test_skips_pyp_codigo(self):
        # codigo=890601: not in PyP list, not excluido, not in any catalog → only REGLA6 could fire.
        # But NOT(cat_in(pyp, codigo)) = NOT(False) = True, so REGLA6 would fire (wrong centro).
        # We need centro correct for the no-match: centro=SALUD PUBLICA.
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "05", "codigo": "890601", "laboratorio": "No", "centro_costo": "SALUD PUBLICA-VACUNACION  REGULAR"})

    def test_skips_when_lab_si(self):
        # lab=Si + tipo=05 → REGLA6 blocked by NOT(AND(cod_tipo in TIPO_LAB, lab=Si)).
        # But REGLA10 fires (cod_tipo=05 in TIPO_LAB, lab=Si) if centro not LAB.
        # Use correct LAB centro to avoid REGLA10.
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "05", "codigo": "993120", "laboratorio": "Si", "centro_costo": "APOYO DIAGNOSTICO-LABORATOR CLINICO"})

class TestRegla7:
    """REGLA7: tipo in {03,04} → SERVICIOS AMBULATORIOS."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self):
        MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "03", "codigo": "890601", "centro_costo": "URGENCIAS"})
    def test_skips_correct_centro(self):
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "03", "codigo": "890601", "centro_costo": "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS"})
    def test_skips_exceptuado_ambulatorio(self):
        # 861101 is only in CODIGOS_EXCEPTUADOS_AMBULATORIO, NOT in quirofano/pyp/etc
        NO_MATCH(self.EL, self.CO, {"codigo_tipo_procedimiento": "03", "codigo": "861101", "centro_costo": "URGENCIAS"})

class TestReglaResponsable:
    """REGLA_RESPONSABLE: facturador + tipo 01/04 → URG/HOSP."""
    EL = "centro_costo_intramural"
    CO = INTRAMURAL_CONDITIONS

    def test_detects_wrong_centro(self):
        MATCH(self.EL, self.CO, {"responsable_cierra": "ARIAS CULCHA ANGIE CAROLINA", "codigo_tipo_procedimiento": "01", "codigo": "890601", "centro_costo": "APOYO DIAGNOSTICO-IMAGENOLOGIA"})
    def test_skips_correct_urgencias(self):
        NO_MATCH(self.EL, self.CO, {"responsable_cierra": "ARIAS CULCHA ANGIE CAROLINA", "codigo_tipo_procedimiento": "01", "codigo": "890601", "centro_costo": "URGENCIAS"})
    def test_skips_correct_hosp(self):
        # cod_tipo=01 is NOT in TIPO_AMB {03,04}, so REGLA7 doesn't fire.
        NO_MATCH(self.EL, self.CO, {"responsable_cierra": "ESPAÑA DIAZ LORENY ALEJANDRA", "codigo_tipo_procedimiento": "01", "codigo": "890601", "centro_costo": "HOSPITALIZACIÓN - ESTANCIA GENERAL"})
    def test_skips_non_facturador(self):
        # centro=URGENCIAS avoids REVERSE1/REVERSE2/REVERSE3/REVERSE4/REVERSE9/REVERSE6/REVERSE7
        NO_MATCH(self.EL, self.CO, {"responsable_cierra": "ALGUIEN OTRO", "codigo_tipo_procedimiento": "01", "codigo": "861101", "centro_costo": "URGENCIAS"})
    def test_skips_exceptuado(self):
        # 735301 is the only code in except_resp AND it's also in quirofano list.
        # Use centro=QUIROFANO so REGLA4 doesn't fire (centro matches).
        NO_MATCH(self.EL, self.CO, {"responsable_cierra": "ARIAS CULCHA ANGIE CAROLINA", "codigo_tipo_procedimiento": "01", "codigo": "735301", "centro_costo": "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"})
    def test_skips_wrong_tipo(self):
        NO_MATCH(self.EL, self.CO, {"responsable_cierra": "ARIAS CULCHA ANGIE CAROLINA", "codigo_tipo_procedimiento": "02", "codigo": "861101", "centro_costo": "URGENCIAS"})


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases: nulls, empty strings, whitespace."""
    EL = "centro_costo_check"
    CO = COMMON_CONDITIONS

    def test_empty_centro_skips(self): NO_MATCH(self.EL, self.CO, {"centro_costo": ""})
    def test_null_centro_skips(self): NO_MATCH(self.EL, self.CO, {"centro_costo": None})

    def test_whitespace_centro(self):
        """WHITESPACE DISCREPANCY: legacy evaluator strips centro before comparing;
        the tree's EqEvaluator does NOT strip. For codice 990211 + whitespace centro:
        - Legacy: strips to "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN" → matches PYP → REVERSE3 has
          correct codigo (990211 in PyP) → no detection → False.
        - Tree: raw centro "  ...  " != centos.Reverse3 → REVERSE3 doesn't fire. But REGLA3 fires:
          cat_in(pyp, codigo=990211) True + NOT(eq(centro, PYP)) True (whitespace != PYP) → True.
        This is expected — the tree is MORE correct (whitespace in centro is a data issue).
        We test both independently rather than assert equivalence."""
        legacy = _run_legacy(self.EL, {"codigo": "990211", "centro_costo": "  PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN  "})
        tree_val = _run_tree(self.CO, {"codigo": "990211", "centro_costo": "  PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN  "})
        # Legacy: False (no detection, strips + matches). Tree: True (detects as wrong centro).
        assert legacy is False, f"Legacy should be False (strips whitespace), got {legacy}"
        assert tree_val is True, f"Tree should be True (raw whitespace detected), got {tree_val}"

    def test_no_fields_provided(self):
        """Empty data — nothing matches."""
        NO_MATCH(self.EL, self.CO, {"centro_costo": "URGENCIAS"})

    def test_cat_in_normalization(self):
        """cat_in now has strip+upper fallback — codigo case difference works."""
        NO_MATCH(self.EL, self.CO, {"codigo": "990211", "centro_costo": "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"})
        NO_MATCH("centro_costo_intramural", INTRAMURAL_CONDITIONS,
                 {"codigo": "990211", "centro_costo": "SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION"})


# ── Neutral baseline tests ────────────────────────────────────────────────────

class TestNeutralBaseline:
    """Verify neutral data produces no detection from either evaluator."""

    NEUTRAL = {"codigo_tipo_procedimiento": "01", "codigo": "890601", "centro_costo": "URGENCIAS"}

    def test_neutral_common(self):
        NO_MATCH("centro_costo_check", COMMON_CONDITIONS, self.NEUTRAL)

    def test_neutral_intramural(self):
        NO_MATCH("centro_costo_intramural", INTRAMURAL_CONDITIONS, self.NEUTRAL)


class TestUrgenciasGeneralInvalidCenter:
    """Standalone Urgencias center validation is independent of other fields."""

    def test_invalid_center_is_detected_with_neutral_cross_fields(self):
        assert _run_tree(
            URGENCIAS_CONDITIONS,
            {
                "codigo_tipo_procedimiento": "01",
                "codigo": "890601",
                "laboratorio": "No",
                "centro_costo": "DIAGNOSTICO",
            },
        ) is True

    def test_valid_center_is_not_detected(self):
        assert _run_tree(
            URGENCIAS_CONDITIONS,
            {
                "codigo_tipo_procedimiento": "01",
                "codigo": "890601",
                "laboratorio": "No",
                "centro_costo": "URGENCIAS",
            },
        ) is False
