"""Migration 013 tests (strict TDD, SQL-text only — zero DB writes).

013 seeds the REMAINING seedable urgencias rules + the hospitalización
centro-costo rule + their catalogs by (nombre, version), idempotent
DELETE+INSERT pattern like 010/011/012. Never hardcodes live row IDs.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "013_seed_rest_urgencias_hosp.sql"

EXPECTED_RULES = {
    # urgencias (5)
    "duplicados_farmacia": "urgencias",
    "profesional_urgencias_valido": "urgencias",
    "revision_cantidad_urgencias": "urgencias",
    "sala_observacion_entidad": "urgencias",
    "sala_observacion_estancia_prolongada": "urgencias",
    # hospitalizacion (1)
    "centro_costo_hospitalizacion_valido": "hospitalizacion",
}

EXPECTED_CATALOGS = (
    "profesionales_urgencias",
    "codigos_exceptuados",
    "centro_costo_pyp",
    "centro_costo_quirofano",
    "centro_costo_hospitalizacion",
    "centros_costo_validos_urgencias",
    "sala_codes",
)

# Catalog keys referenced via operador='cat_in' by the seeded trees.
EXPECTED_CAT_IN_KEYS = (
    "profesionales_urgencias",
    "codigos_exceptuados",
    "centro_costo_pyp",
    "centro_costo_quirofano",
    "centro_costo_hospitalizacion",
    "centros_costo_validos_urgencias",
)


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """SQL lines with full-line comments stripped (cat_in audit ignores comments)."""
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def test_013_file_exists() -> None:
    assert MIGRATION.exists(), "013 migration file missing"


def test_013_planned_after_012() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "012_seed_odonto_equipos_transversal" in planned
    assert "013_seed_rest_urgencias_hosp" in planned
    assert planned.index("012_seed_odonto_equipos_transversal") < planned.index(
        "013_seed_rest_urgencias_hosp"
    )


def test_013_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False


def test_013_upserts_each_rule_by_name_version() -> None:
    text = _text()
    for name, dominio in EXPECTED_RULES.items():
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'%s',\s*'active',\s*1," % (re.escape(name), re.escape(dominio)),
            re.DOTALL,
        )
        assert pattern.search(text), f"rule {name} not upserted as ('name', {dominio}, active, v1)"
    assert text.count("ON CONFLICT (nombre, version) DO UPDATE") >= len(EXPECTED_RULES)


def test_013_rebuilds_conditions_by_name() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        assert re.search(
            r"WHERE nombre = '%s' AND version = 1" % re.escape(name), text
        ), f"rule {name} conditions not resolved by (nombre, version)"
    assert text.count("DELETE FROM condiciones WHERE regla_id = ") >= len(EXPECTED_RULES)


def test_013_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None, "hardcoded regla_id literal found"
    assert re.search(r"padre_id\s*=\s*\d+", code) is None, "hardcoded padre_id literal found"


def test_013_no_transaction_control() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None


def test_013_seeds_expected_catalogs_additively() -> None:
    lowered = _text().lower()
    for key in EXPECTED_CATALOGS:
        assert key in lowered, f"catalog {key} missing"
    assert lowered.count("where not exists (select 1 from catalogos where key =") >= len(
        EXPECTED_CATALOGS
    )


def test_013_seeded_trees_use_expected_cat_in_keys() -> None:
    """Seeded profesional/centro_costo trees resolve via cat_in; sala evaluator trees use none."""
    code = "\n".join(_code_lines(_text()))
    assert "'cat_in'" in code, "013 seeds no cat_in conditions — catalog keys would dangle"
    for key in EXPECTED_CAT_IN_KEYS:
        assert re.search(
            r"'cat_in',\s*'invoice\.[a-z_]+',\s*(to_jsonb\('%s'::text\)|'\"%s\"')"
            % (re.escape(key), re.escape(key)),
            code,
        ), f"cat_in key {key} not referenced by any seeded tree"
    # Every cat_in key used in code must be seeded additively in this file.
    used = set(re.findall(r"'cat_in',\s*'invoice\.[a-z_]+',\s*(?:to_jsonb\('([a-z_]+)'::text\)|'\"([a-z_]+)\"')", code))
    used_keys = {a or b for a, b in used}
    assert used_keys <= set(EXPECTED_CATALOGS), f"cat_in keys not seeded: {used_keys - set(EXPECTED_CATALOGS)}"


def test_013_sala_rules_use_evaluator_shape() -> None:
    """The two sala rules seed the dev-active sala_obs_check single cond (stale AND trees excluded)."""
    code = "\n".join(_code_lines(_text()))
    assert code.count("'sala_obs_check'") == 2, "expected exactly 2 sala_obs_check conds (entidad + estancia)"


def test_013_duplicados_parents_both_atomics_under_root() -> None:
    """duplicados_farmacia corrects the final_rules mis-parenting: gt must sit under the AND root."""
    text = _text()
    idx = text.find("'duplicados_farmacia', 'Detecta posibles duplicados")
    assert idx != -1
    window = text[idx : idx + 2500]
    assert "'AND'" in window
    assert "'invoice.tipo_factura_descripcion'" in window
    assert "'invoice.cantidad'" in window
    # Both atomics resolve their parent from the captured root id (never MAX(id)).
    assert window.count("_root_id") >= 3
    assert "MAX(id)" not in window and "MAX(c.id)" not in window


def test_013_hosp_seeds_full_52cond_tree() -> None:
    """centro_costo_hospitalizacion_valido carries the F14 base + orden-11 branch (dev v9 verbatim)."""
    code = "\n".join(_code_lines(_text()))
    for key in (
        "codigos_exceptuados",
        "centro_costo_pyp",
        "centro_costo_quirofano",
        "centro_costo_hospitalizacion",
        "centros_costo_validos_urgencias",
    ):
        assert key in code, f"hosp tree missing cat_in key {key}"
    assert ", 11)" in code, "hosp tree missing the dev-verbatim orden-11 branch"


def test_013_excludes_noted_rules() -> None:
    text = _text()
    code = "\n".join(_code_lines(text))
    # Excluded rules may be named in header comments, never in executable code.
    for excluded in (
        "duplicados_farmacia_v2",
        "ide_contrato_reverse_urgencias_valido",
        "revision_cantidad_v2",
        "sala_obs_check_set",
        "ide_contrato_odontologia_valido",
        "detect_duplicados_base",
    ):
        assert excluded not in code, f"excluded rule {excluded} seeded in executable code"
        assert excluded in text, f"excluded rule {excluded} not documented in header"
    assert "Excluded" in text
    assert "version = 2" not in text
    assert "version <> 1" not in text


def test_013_guarded_schema_alters_like_010() -> None:
    lowered = _text().lower()
    assert "information_schema" in lowered
    assert "operador" in lowered and "valor_esperado" in lowered


def test_013_backfills_rule_base_id() -> None:
    text = _text()
    assert "rule_base_id" in text
    assert re.search(r"rule_base_id\s*=\s*id", text) is not None
    for name in ("duplicados_farmacia", "centro_costo_hospitalizacion_valido"):
        assert name in text
