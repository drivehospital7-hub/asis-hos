"""Migration 024 tests (SQL-text + hermetic firing — zero DB writes).

024 converges the 022 urg_ rules to the prod bridge shape:
  profesional_urg_<family> -> profesional_<family> (9 rules, final names),
  mirror dominio 'hospitalizacion', NO eq guard on
  invoice.tipo_factura_descripcion, bridge scope (hospitalizacion, urgencias)
  via regla_dominios.

Bridge condition counts (no tipo guard):
  trabajadora_social, psicologa, nutricionista, fisioterapeuta,
  jefe_enfermeria, odontologo: 4 each (root AND + cat_in prof orden 1 +
  NOT orden 2 + inner cat_in codigo).
  medico_excluido: 3 (root AND + prof orden 1 + cat_in excluidos orden 2).
  bacteriologa_lab: 8 (root + prof + NOT_lab(2) + inner AND +
  tipo_lab + lab=Si + NOT_exc(3) + inner excepciones).
  medico_lab: 4 (root + prof + tipo_lab + lab=Si).
Total: 39 conditions. 21 catalogs re-run from 022; reuses
codigos_tipo_procedimiento_laboratorio (never redefined).

024 converges both directions (fresh DB: 022 urg_ + 024 renames+rebuilds;
prod: upserts refresh activo/grupo_error, guarded inserts are no-ops).
NOTE: this test was updated to the convergent form by eye against the SQL
text; it was not executed against a live DB (collect-only validation).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "024_reconcile_profesional_bridge.sql"
NEXT_MIGRATION = MIGRATIONS_DIR / "025_seed_duplicado_02_lab.sql"

URG_TO_FINAL = {
    "profesional_urg_trabajadora_social": "profesional_trabajadora_social",
    "profesional_urg_psicologa": "profesional_psicologa",
    "profesional_urg_nutricionista": "profesional_nutricionista",
    "profesional_urg_fisioterapeuta": "profesional_fisioterapeuta",
    "profesional_urg_jefe_enfermeria": "profesional_jefe_enfermeria",
    "profesional_urg_odontologo": "profesional_odontologo",
    "profesional_urg_medico_excluido": "profesional_medico_excluido",
    "profesional_urg_bacteriologa_lab": "profesional_bacteriologa_lab",
    "profesional_urg_medico_lab": "profesional_medico_lab",
}

EXPECTED_RULES = {final: "hospitalizacion" for final in URG_TO_FINAL.values()}

EXPECTED_COUNTS = {
    "profesional_trabajadora_social": 4,
    "profesional_psicologa": 4,
    "profesional_nutricionista": 4,
    "profesional_fisioterapeuta": 4,
    "profesional_jefe_enfermeria": 4,
    "profesional_odontologo": 4,
    "profesional_medico_excluido": 3,
    "profesional_bacteriologa_lab": 8,
    "profesional_medico_lab": 4,
}

EXPECTED_CATALOGS = (
    "profesionales_urgencias_trabajadora_social",
    "profesionales_urgencias_psicologa",
    "profesionales_urgencias_nutricionista",
    "profesionales_urgencias_fisioterapeuta",
    "profesionales_urgencias_jefe_enfermeria",
    "profesionales_urgencias_odontologo",
    "profesionales_urgencias_medico",
    "profesionales_urgencias_bacteriologa",
    "profesionales_odontologia_higienista",
    "profesionales_odontologia_odontologo",
    "profesionales_equipos_basicos_higienista",
    "profesionales_equipos_basicos_odontologo",
    "codigos_trabajadora_social",
    "codigos_psicologa",
    "codigos_nutricionista",
    "codigos_fisioterapeuta",
    "codigos_jefe_enfermeria",
    "codigos_odontologo_urg",
    "codigos_excluidos_medico",
    "excepciones_bacteriologa",
    "codigos_pyp_higienista",
)

# Rules 024 must never reference (other-domain mirrors / existence checks).
PROTECTED_NAMES = (
    "profesional_hosp_",
    "profesional_odon_",
    "profesional_eqb_",
    "_valido",
)


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def _rule_window(text: str, name: str) -> str:
    start = text.find("    '%s',\n" % name)
    assert start != -1, "rule %s upsert missing" % name
    rest = text[start:]
    nxt = rest.find("INSERT INTO reglas", 10)
    return rest[:nxt] if nxt != -1 else rest


def test_024_file_exists() -> None:
    assert MIGRATION.exists(), "024 migration file missing"


def test_024_planned_after_023_before_025() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "023_regla_dominios" in planned
    assert "024_reconcile_profesional_bridge" in planned
    assert "025_seed_duplicado_02_lab" in planned
    assert planned.index("023_regla_dominios") < planned.index(
        "024_reconcile_profesional_bridge"
    )
    assert planned.index("024_reconcile_profesional_bridge") < planned.index(
        "025_seed_duplicado_02_lab"
    )


def test_024_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False
    assert should_skip_evidence(NEXT_MIGRATION.name, include_evidence=False) is False


def test_024_renames_each_urg_rule_to_final() -> None:
    text = _text()
    for urg_name, final_name in URG_TO_FINAL.items():
        assert "SET nombre = '%s'" % final_name in text, "rename to %s missing" % final_name
        assert "WHERE nombre = '%s' AND version = 1" % urg_name in text, (
            "rename source %s missing" % urg_name
        )
        assert "NOT EXISTS (SELECT 1 FROM reglas WHERE nombre = '%s' AND version = 1)" % final_name in text, (
            "rename of %s not guarded against existing final" % final_name
        )


def test_024_upserts_each_final_rule_narrow_conflict() -> None:
    text = _text()
    for final_name, dominio in EXPECTED_RULES.items():
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'%s',\s*'active',\s*1," % (re.escape(final_name), re.escape(dominio)),
            re.DOTALL,
        )
        assert pattern.search(text), "rule %s not upserted" % final_name
    assert text.count(
        "ON CONFLICT (nombre, version) DO UPDATE SET activo = true, grupo_error = 'Profesionales'"
    ) == len(EXPECTED_RULES)


def test_024_rebuilds_only_guard_shaped_trees() -> None:
    text = _text()
    for final_name in EXPECTED_RULES:
        window = _rule_window(text, final_name)
        assert "g.operador = 'eq' AND g.fuente_datos = 'invoice.tipo_factura_descripcion'" in window, (
            "rule %s missing guard-shaped rebuild trigger" % final_name
        )


def test_024_no_tipo_guard_values() -> None:
    code = "\n".join(_code_lines(_text()))
    assert '"Urgencias"' not in code, "bridge must not filter on Urgencias literal"
    assert '"Hospitalización"' not in code, "bridge must not filter on Hospitalización literal"
    assert "'atomic', 'eq', 'invoice.tipo_factura_descripcion'" not in code


def test_024_seeds_expected_bridge_cond_counts() -> None:
    text = _text()
    for name, expected in EXPECTED_COUNTS.items():
        window = _rule_window(text, name)
        found = window.count("INSERT INTO condiciones")
        assert found == expected, "rule %s: seeded %d conds, expected %d" % (name, found, expected)
    assert text.count("INSERT INTO condiciones") == sum(EXPECTED_COUNTS.values()) == 39


def test_024_prof_orden_before_not_orden() -> None:
    text = _text()
    not_bearing = [n for n in EXPECTED_RULES if n not in (
        "profesional_medico_excluido", "profesional_medico_lab")]  # positive-match bridges
    assert len(not_bearing) == 7
    for name in not_bearing:
        window = _rule_window(text, name)
        prof_pos = window.find("'invoice.codigo_profesional'")
        not_pos = window.find("'composite', 'NOT'")
        assert prof_pos != -1 and not_pos != -1 and prof_pos < not_pos, (
            "rule %s: prof must precede NOT" % name
        )


def test_024_ensures_both_bridge_rows() -> None:
    text = _text()
    assert "CREATE TABLE IF NOT EXISTS regla_dominios" in text
    assert "CREATE INDEX IF NOT EXISTS ix_regla_dominios_dominio" in text
    for name in EXPECTED_RULES:
        window = _rule_window(text, name)
        assert "rd.dominio = 'hospitalizacion'" in window, "rule %s missing hospitalizacion bridge" % name
        assert "rd.dominio = 'urgencias'" in window, "rule %s missing urgencias bridge" % name
    assert text.count("INSERT INTO regla_dominios") == 2 * len(EXPECTED_RULES) == 18


def test_024_reruns_expected_catalogs() -> None:
    code = "\n".join(_code_lines(_text()))
    assert code.count("INSERT INTO catalogos") == len(EXPECTED_CATALOGS) == 21
    for key in EXPECTED_CATALOGS:
        assert "'%s'" % key in code, "catalog %s missing" % key
        assert re.search(
            r"WHERE NOT EXISTS \(SELECT 1 FROM catalogos WHERE key = '%s'\)" % re.escape(key),
            code,
        ), "catalog %s not additive-guarded" % key


def test_024_reuses_lab_catalog_without_redefining() -> None:
    code = "\n".join(_code_lines(_text()))
    assert code.count('"codigos_tipo_procedimiento_laboratorio"') == 2
    assert "key = 'codigos_tipo_procedimiento_laboratorio'" not in code


def test_024_grupo_error_and_detail_fields() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        window = _rule_window(text, name)
        assert "'Profesionales'" in window, "rule %s missing grupo_error" % name
        assert "'codigo_profesional,procedimiento'" in window, "rule %s missing detalle_a" % name
        assert "'Cód: {codigo_profesional}'" in window, "rule %s missing detalle_b" % name


def test_024_only_expected_operators() -> None:
    code = "\n".join(_code_lines(_text()))
    ops = set(re.findall(r"'(AND|OR|NOT|eq|cat_in|in|gt|gte|lt|lte)'", code))
    assert ops <= {"AND", "NOT", "eq", "cat_in"}, "unexpected operators: %s" % ops


def test_024_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None
    assert re.search(r"padre_id\s*=\s*\d+", code) is None


def test_024_no_transaction_control_or_max_id() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None
    assert "MAX(id)" not in code and "MAX(c.id)" not in code


def test_024_single_active_v1_per_rule() -> None:
    text = _text()
    assert "version = 2" not in text
    assert "version <> 1" not in text


def test_024_never_touches_protected_rules() -> None:
    code = "\n".join(_code_lines(_text()))
    for protected in PROTECTED_NAMES:
        assert protected not in code, "024 must not reference %s*" % protected


class _FakeSession:
    def __init__(self, catalogs: dict) -> None:
        self._catalogs = catalogs

    def execute(self, _stmt: Any, params: dict | None = None) -> Any:
        val = self._catalogs.get((params or {}).get("key", ""))

        class _Result:
            def fetchone(self) -> Any:
                return (val,) if val is not None else None

        return _Result()


_CATALOGS = {
    "profesionales_urgencias_trabajadora_social": ["01235", "03568"],
    "profesionales_urgencias_medico": ["01293", "02249"],
    "profesionales_urgencias_bacteriologa": ["02217", "03374"],
    "codigos_trabajadora_social": ["37701", "890409"],
    "codigos_excluidos_medico": ["890409", "37701", "890408"],
    "codigos_tipo_procedimiento_laboratorio": ["02", "05"],
    "excepciones_bacteriologa": ["903883", "904903"],
}


def _conds(specs: list) -> list:
    out = []
    for i, (pid, tipo, op, fuente, esperado) in enumerate(specs, start=1):
        out.append({
            "id": i, "padre_id": pid, "tipo": tipo, "operador": op,
            "fuente_datos": fuente, "valor_esperado": esperado, "orden": 0,
        })
    return out


def _fires(specs: list, invoice: dict) -> bool:
    from app.services.engine.condition_evaluator import ConditionEvaluator
    from app.services.engine.context import EvaluationContext

    ev = ConditionEvaluator()
    tree = ev.build_tree(_conds(specs))
    assert tree is not None
    ctx = EvaluationContext(invoice_data=invoice, session=_FakeSession(_CATALOGS))
    return bool(ev.evaluate(tree, ctx)["outcome"])


# Bridge shapes: root AND, prof orden 1, no tipo guard.
_TS_B = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_urgencias_trabajadora_social"),
    (1, "composite", "NOT", None, None),
    (3, "atomic", "cat_in", "invoice.codigo", "codigos_trabajadora_social"),
]

_MED_EXCL_B = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional", "profesionales_urgencias_medico"),
    (1, "atomic", "cat_in", "invoice.codigo", "codigos_excluidos_medico"),
]

_BACT_B = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_urgencias_bacteriologa"),
    (1, "composite", "NOT", None, None),
    (3, "composite", "AND", None, None),
    (4, "atomic", "cat_in", "invoice.codigo_tipo_procedimiento",
     "codigos_tipo_procedimiento_laboratorio"),
    (4, "atomic", "eq", "invoice.laboratorio", "Si"),
    (1, "composite", "NOT", None, None),
    (7, "atomic", "cat_in", "invoice.codigo", "excepciones_bacteriologa"),
]

_MED_LAB_B = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional", "profesionales_urgencias_medico"),
    (1, "atomic", "cat_in", "invoice.codigo_tipo_procedimiento",
     "codigos_tipo_procedimiento_laboratorio"),
    (1, "atomic", "eq", "invoice.laboratorio", "Si"),
]


class TestFiringBridge:
    def test_ts_fires_on_forbidden_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03568",
               "codigo": "890201"}
        assert _fires(_TS_B, inv) is True

    def test_ts_fires_regardless_of_tipo(self) -> None:
        # Bridge has no tipo guard: scope comes from regla_dominios.
        inv = {"tipo_factura_descripcion": "Hospitalización", "codigo_profesional": "03568",
               "codigo": "890201"}
        assert _fires(_TS_B, inv) is True

    def test_ts_silent_on_allowed_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03568",
               "codigo": "890409"}
        assert _fires(_TS_B, inv) is False

    def test_ts_silent_for_other_prof(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890201"}
        assert _fires(_TS_B, inv) is False

    def test_medico_excluido_fires(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890409"}
        assert _fires(_MED_EXCL_B, inv) is True

    def test_medico_excluido_silent_neutral_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890201"}
        assert _fires(_MED_EXCL_B, inv) is False

    def test_medico_lab_fires(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo_tipo_procedimiento": "02", "laboratorio": "Si"}
        assert _fires(_MED_LAB_B, inv) is True

    def test_medico_lab_silent_no_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No"}
        assert _fires(_MED_LAB_B, inv) is False

    def test_bacteriologa_fires_without_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No", "codigo": "901210"}
        assert _fires(_BACT_B, inv) is True

    def test_bacteriologa_silent_with_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "02", "laboratorio": "Si", "codigo": "901210"}
        assert _fires(_BACT_B, inv) is False

    def test_bacteriologa_silent_on_exception_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No", "codigo": "904903"}
        assert _fires(_BACT_B, inv) is False
