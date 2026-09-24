"""Migration 022 tests (SQL-text + hermetic firing — zero DB writes).

022 moves the legacy "tipo de profesional -> codigos permitidos" mapping into
the engine (Approach A: data only, no new code) from:
  app/services/urgencias/profesionales_urgencias.py (+ constants/urgencias.py)
  app/services/odontologia/profesionales.py         (+ constants/odontologia.py)
  app/services/equipos_basicos/profesionales.py     (+ constants/equipos_basicos.py)

Seeded (22 rules, all active v1, prioridad 40, severidad error,
grupo_error 'Profesionales'):
  urgencias (9, filtro tipo=Urgencias):
    profesional_urg_{trabajadora_social, psicologa, nutricionista,
      fisioterapeuta, jefe_enfermeria, odontologo} (5 conds c/u),
    profesional_urg_medico_excluido (4), profesional_urg_bacteriologa_lab (9),
    profesional_urg_medico_lab (5).
  hospitalizacion (9, espejo con filtro 'Hospitalización', mismos catalogos).
  odontologia (2, sin filtro de tipo): profesional_odon_higienista (4),
    profesional_odon_odontologo_pyp (5).
  equipos_basicos (2, espejo odonto).
Total: 114 condiciones. 21 catalogos nuevos; reusa
codigos_tipo_procedimiento_laboratorio (no lo redefine).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "022_seed_profesional_codigo_map.sql"

EXPECTED_RULES = {
    "profesional_urg_trabajadora_social": "urgencias",
    "profesional_urg_psicologa": "urgencias",
    "profesional_urg_nutricionista": "urgencias",
    "profesional_urg_fisioterapeuta": "urgencias",
    "profesional_urg_jefe_enfermeria": "urgencias",
    "profesional_urg_odontologo": "urgencias",
    "profesional_urg_medico_excluido": "urgencias",
    "profesional_urg_bacteriologa_lab": "urgencias",
    "profesional_urg_medico_lab": "urgencias",
    "profesional_hosp_trabajadora_social": "hospitalizacion",
    "profesional_hosp_psicologa": "hospitalizacion",
    "profesional_hosp_nutricionista": "hospitalizacion",
    "profesional_hosp_fisioterapeuta": "hospitalizacion",
    "profesional_hosp_jefe_enfermeria": "hospitalizacion",
    "profesional_hosp_odontologo": "hospitalizacion",
    "profesional_hosp_medico_excluido": "hospitalizacion",
    "profesional_hosp_bacteriologa_lab": "hospitalizacion",
    "profesional_hosp_medico_lab": "hospitalizacion",
    "profesional_odon_higienista": "odontologia",
    "profesional_odon_odontologo_pyp": "odontologia",
    "profesional_eqb_higienista": "equipos_basicos",
    "profesional_eqb_odontologo_pyp": "equipos_basicos",
}

EXPECTED_COUNTS = {
    "profesional_urg_trabajadora_social": 5,
    "profesional_urg_psicologa": 5,
    "profesional_urg_nutricionista": 5,
    "profesional_urg_fisioterapeuta": 5,
    "profesional_urg_jefe_enfermeria": 5,
    "profesional_urg_odontologo": 5,
    "profesional_urg_medico_excluido": 4,
    "profesional_urg_bacteriologa_lab": 9,
    "profesional_urg_medico_lab": 5,
    "profesional_hosp_trabajadora_social": 5,
    "profesional_hosp_psicologa": 5,
    "profesional_hosp_nutricionista": 5,
    "profesional_hosp_fisioterapeuta": 5,
    "profesional_hosp_jefe_enfermeria": 5,
    "profesional_hosp_odontologo": 5,
    "profesional_hosp_medico_excluido": 4,
    "profesional_hosp_bacteriologa_lab": 9,
    "profesional_hosp_medico_lab": 5,
    "profesional_odon_higienista": 4,
    "profesional_odon_odontologo_pyp": 5,
    "profesional_eqb_higienista": 4,
    "profesional_eqb_odontologo_pyp": 5,
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


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def _rule_window(text: str, name: str) -> str:
    start = text.find("'%s'" % name)
    assert start != -1, "rule %s upsert missing" % name
    rest = text[start:]
    nxt = rest.find("INSERT INTO reglas", 10)
    return rest[:nxt] if nxt != -1 else rest


def test_022_file_exists() -> None:
    assert MIGRATION.exists(), "022 migration file missing"


def test_022_planned_after_021() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "021_live_detail_keys" in planned
    assert "022_seed_profesional_codigo_map" in planned
    assert planned.index("021_live_detail_keys") < planned.index(
        "022_seed_profesional_codigo_map"
    )


def test_022_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False


def test_022_upserts_each_rule_by_name_version() -> None:
    text = _text()
    for name, dominio in EXPECTED_RULES.items():
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'%s',\s*'active',\s*1," % (re.escape(name), re.escape(dominio)),
            re.DOTALL,
        )
        assert pattern.search(text), "rule %s not upserted" % name
    assert text.count("ON CONFLICT (nombre, version) DO UPDATE") >= len(EXPECTED_RULES)


def test_022_rebuilds_conditions_by_name() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        assert re.search(
            r"WHERE nombre = '%s' AND version = 1" % re.escape(name), text
        ), "rule %s conditions not resolved by name" % name
    assert text.count("DELETE FROM condiciones WHERE regla_id = ") >= len(EXPECTED_RULES)


def test_022_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None
    assert re.search(r"padre_id\s*=\s*\d+", code) is None


def test_022_no_transaction_control_or_max_id() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None
    assert "MAX(id)" not in code and "MAX(c.id)" not in code


def test_022_seeds_expected_cond_counts() -> None:
    text = _text()
    for name, expected in EXPECTED_COUNTS.items():
        window = _rule_window(text, name)
        found = window.count("VALUES (rid,")
        assert found == expected, "rule %s: seeded %d conds, expected %d" % (name, found, expected)
    assert text.count("VALUES (rid,") == sum(EXPECTED_COUNTS.values()) == 114


def test_022_seeds_expected_catalogs() -> None:
    code = "\n".join(_code_lines(_text()))
    assert code.count("INSERT INTO catalogos") == len(EXPECTED_CATALOGS) == 21
    for key in EXPECTED_CATALOGS:
        assert "'%s'" % key in code, "catalog %s missing" % key
        assert re.search(
            r"WHERE NOT EXISTS \(SELECT 1 FROM catalogos WHERE key = '%s'\)" % re.escape(key),
            code,
        ), "catalog %s not additive-guarded" % key


def test_022_reuses_lab_catalog_without_redefining() -> None:
    code = "\n".join(_code_lines(_text()))
    assert code.count('"codigos_tipo_procedimiento_laboratorio"') == 4
    assert "key = 'codigos_tipo_procedimiento_laboratorio'" not in code


def test_022_grupo_error_and_detail_fields() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        window = _rule_window(text, name)
        assert "'Profesionales'" in window, "rule %s missing grupo_error" % name
        assert "'codigo_profesional,procedimiento'" in window, "rule %s missing detalle_a" % name
        assert "'Cód: {codigo_profesional}'" in window, "rule %s missing detalle_b" % name


def test_022_only_expected_operators() -> None:
    code = "\n".join(_code_lines(_text()))
    ops = set(re.findall(r"'(AND|OR|NOT|eq|cat_in|in|gt|gte|lt|lte)'", code))
    assert ops <= {"AND", "NOT", "eq", "cat_in"}, "unexpected operators: %s" % ops


def test_022_single_active_v1_per_rule() -> None:
    text = _text()
    assert "version = 2" not in text
    assert "version <> 1" not in text
    for name in EXPECTED_RULES:
        assert text.count("WHERE nombre = '%s' AND version = 1" % name) == 1


def test_022_hosp_mirrors_urg_shapes() -> None:
    text = _text()
    pairs = [
        ("profesional_urg_trabajadora_social", "profesional_hosp_trabajadora_social"),
        ("profesional_urg_medico_excluido", "profesional_hosp_medico_excluido"),
        ("profesional_urg_bacteriologa_lab", "profesional_hosp_bacteriologa_lab"),
        ("profesional_urg_medico_lab", "profesional_hosp_medico_lab"),
    ]
    for urg_name, hosp_name in pairs:
        urg_ops = re.findall(r"'(AND|NOT|eq|cat_in)'", _rule_window(text, urg_name))
        hosp_ops = re.findall(r"'(AND|NOT|eq|cat_in)'", _rule_window(text, hosp_name))
        assert urg_ops == hosp_ops, "%s shape drifted from %s" % (hosp_name, urg_name)
        assert '"Hospitalización"' in _rule_window(text, hosp_name)


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
    "profesionales_odontologia_higienista": ["01329", "01330", "03698"],
    "profesionales_odontologia_odontologo": ["01251", "03007", "03424"],
    "codigos_trabajadora_social": ["37701", "890409"],
    "codigos_excluidos_medico": ["890409", "37701", "890408"],
    "codigos_tipo_procedimiento_laboratorio": ["02", "05"],
    "excepciones_bacteriologa": ["903883", "904903"],
    "codigos_pyp_higienista": ["990212", "997002", "997106", "997107", "997301", "P0000011"],
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


_TS = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "eq", "invoice.tipo_factura_descripcion", "Urgencias"),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_urgencias_trabajadora_social"),
    (1, "composite", "NOT", None, None),
    (4, "atomic", "cat_in", "invoice.codigo", "codigos_trabajadora_social"),
]

_MED_EXCL = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "eq", "invoice.tipo_factura_descripcion", "Urgencias"),
    (1, "atomic", "cat_in", "invoice.codigo_profesional", "profesionales_urgencias_medico"),
    (1, "atomic", "cat_in", "invoice.codigo", "codigos_excluidos_medico"),
]

_BACT = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "eq", "invoice.tipo_factura_descripcion", "Urgencias"),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_urgencias_bacteriologa"),
    (1, "composite", "NOT", None, None),
    (4, "composite", "AND", None, None),
    (5, "atomic", "cat_in", "invoice.codigo_tipo_procedimiento",
     "codigos_tipo_procedimiento_laboratorio"),
    (5, "atomic", "eq", "invoice.laboratorio", "Si"),
    (1, "composite", "NOT", None, None),
    (8, "atomic", "cat_in", "invoice.codigo", "excepciones_bacteriologa"),
]

_MED_LAB = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "eq", "invoice.tipo_factura_descripcion", "Urgencias"),
    (1, "atomic", "cat_in", "invoice.codigo_profesional", "profesionales_urgencias_medico"),
    (1, "atomic", "cat_in", "invoice.codigo_tipo_procedimiento",
     "codigos_tipo_procedimiento_laboratorio"),
    (1, "atomic", "eq", "invoice.laboratorio", "Si"),
]

_HIG = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_odontologia_higienista"),
    (1, "composite", "NOT", None, None),
    (3, "atomic", "cat_in", "invoice.codigo", "codigos_pyp_higienista"),
]

_ODO_PYP = [
    (None, "composite", "AND", None, None),
    (1, "atomic", "cat_in", "invoice.codigo_profesional",
     "profesionales_odontologia_odontologo"),
    (1, "atomic", "cat_in", "invoice.codigo", "codigos_pyp_higienista"),
    (1, "composite", "NOT", None, None),
    (4, "atomic", "eq", "invoice.codigo", "P0000011"),
]


class TestFiringTipoCodigo:
    def test_ts_fires_on_forbidden_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03568",
               "codigo": "890201"}
        assert _fires(_TS, inv) is True

    def test_ts_silent_on_allowed_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03568",
               "codigo": "890409"}
        assert _fires(_TS, inv) is False

    def test_ts_silent_for_other_tipo(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890201"}
        assert _fires(_TS, inv) is False

    def test_ts_silent_for_other_dominio(self) -> None:
        inv = {"tipo_factura_descripcion": "Hospitalización", "codigo_profesional": "03568",
               "codigo": "890201"}
        assert _fires(_TS, inv) is False

    def test_medico_excluido_fires(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890409"}
        assert _fires(_MED_EXCL, inv) is True

    def test_medico_excluido_silent_neutral_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo": "890201"}
        assert _fires(_MED_EXCL, inv) is False

    def test_medico_lab_fires(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo_tipo_procedimiento": "02", "laboratorio": "Si"}
        assert _fires(_MED_LAB, inv) is True

    def test_medico_lab_silent_no_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "01293",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No"}
        assert _fires(_MED_LAB, inv) is False

    def test_bacteriologa_fires_without_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No", "codigo": "901210"}
        assert _fires(_BACT, inv) is True

    def test_bacteriologa_silent_with_lab(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "02", "laboratorio": "Si", "codigo": "901210"}
        assert _fires(_BACT, inv) is False

    def test_bacteriologa_silent_on_exception_code(self) -> None:
        inv = {"tipo_factura_descripcion": "Urgencias", "codigo_profesional": "03374",
               "codigo_tipo_procedimiento": "01", "laboratorio": "No", "codigo": "904903"}
        assert _fires(_BACT, inv) is False

    def test_higienista_fires_non_pyp(self) -> None:
        inv = {"codigo_profesional": "01329", "codigo": "890201"}
        assert _fires(_HIG, inv) is True

    def test_higienista_silent_pyp(self) -> None:
        inv = {"codigo_profesional": "01329", "codigo": "997002"}
        assert _fires(_HIG, inv) is False

    def test_odontologo_fires_pyp(self) -> None:
        inv = {"codigo_profesional": "03424", "codigo": "997002"}
        assert _fires(_ODO_PYP, inv) is True

    def test_odontologo_silent_p0000011(self) -> None:
        inv = {"codigo_profesional": "03424", "codigo": "P0000011"}
        assert _fires(_ODO_PYP, inv) is False

    def test_odontologo_silent_non_pyp(self) -> None:
        inv = {"codigo_profesional": "03424", "codigo": "890201"}
        assert _fires(_ODO_PYP, inv) is False
