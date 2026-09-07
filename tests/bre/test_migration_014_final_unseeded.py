"""Migration 014 tests (strict TDD, SQL-text only — zero DB writes).

014 seeds the FINAL 6 engine rules with no seed coverage, ported faithfully
from the live dev-active asis_hos trees, by (nombre, version), idempotent
DELETE+INSERT pattern like 010/011/012/013. Never hardcodes live row IDs.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "014_seed_final_unseeded_rules.sql"

EXPECTED_RULES = {
    # odontologia (1)
    "ide_contrato_odontologia_valido": "odontologia",
    # transversal (1)
    "detect_duplicados_base": "transversal",
    # urgencias (4)
    "duplicados_farmacia_v2": "urgencias",
    "ide_contrato_reverse_urgencias_valido": "urgencias",
    "revision_cantidad_v2": "urgencias",
    "sala_obs_check_set": "urgencias",
}

# Live dev-active per-rule condition counts (read-only SELECT from asis_hos).
EXPECTED_COUNTS = {
    "ide_contrato_odontologia_valido": 111,
    "detect_duplicados_base": 1,
    "duplicados_farmacia_v2": 1,
    "ide_contrato_reverse_urgencias_valido": 21,
    "revision_cantidad_v2": 1,
    "sala_obs_check_set": 4,
}


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """SQL lines with full-line comments stripped (audits ignore comments)."""
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def _rule_window(text: str, name: str) -> str:
    """Executable window for one rule: from its upsert to the next rule block."""
    start = text.find(f"'{name}', '")
    assert start != -1, f"rule {name} upsert missing"
    rest = text[start + len(name):]
    nxt = re.search(r"\n-- -{10,}\n-- [a-z_0-9]+ \((?:odontologia|transversal|urgencias),", rest)
    return rest[: nxt.start()] if nxt else rest


def test_014_file_exists() -> None:
    assert MIGRATION.exists(), "014 migration file missing"


def test_014_planned_after_013() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "013_seed_rest_urgencias_hosp" in planned
    assert "014_seed_final_unseeded_rules" in planned
    assert planned.index("013_seed_rest_urgencias_hosp") < planned.index(
        "014_seed_final_unseeded_rules"
    )


def test_014_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False


def test_014_upserts_each_rule_by_name_version() -> None:
    text = _text()
    for name, dominio in EXPECTED_RULES.items():
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'%s',\s*'active',\s*1," % (re.escape(name), re.escape(dominio)),
            re.DOTALL,
        )
        assert pattern.search(text), f"rule {name} not upserted as ('name', {dominio}, active, v1)"
    assert text.count("ON CONFLICT (nombre, version) DO UPDATE") >= len(EXPECTED_RULES)


def test_014_rebuilds_conditions_by_name() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        assert re.search(
            r"WHERE nombre = '%s' AND version = 1" % re.escape(name), text
        ), f"rule {name} conditions not resolved by (nombre, version)"
    assert text.count("DELETE FROM condiciones WHERE regla_id = ") >= len(EXPECTED_RULES)


def test_014_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None, "hardcoded regla_id literal found"
    assert re.search(r"padre_id\s*=\s*\d+", code) is None, "hardcoded padre_id literal found"


def test_014_no_transaction_control_or_max_id() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None
    assert "MAX(id)" not in code and "MAX(c.id)" not in code


def test_014_seeds_live_faithful_cond_counts() -> None:
    """Per-rule INSERT counts match the live dev-active trees (111/1/1/21/1/4)."""
    text = _text()
    for name, expected in EXPECTED_COUNTS.items():
        window = _rule_window(text, name)
        found = window.count("VALUES (_regla_id,")
        assert found == expected, f"rule {name}: seeded {found} conds, live has {expected}"
    assert text.count("VALUES (_regla_id,") == sum(EXPECTED_COUNTS.values()) == 139


def test_014_odonto_ports_full_111cond_tree() -> None:
    """Odonto OR root + 20 AND branches; partial phase3 seed is NOT used."""
    text = _text()
    window = _rule_window(text, "ide_contrato_odontologia_valido")
    assert "'OR'" in window and window.count("'AND'") == 20
    for entidad in ("ESS118", "ESSC18", "EPSS41", "EPSI05", "EPS037",
                    "ESS062", "ESSC62", "EPSS005", "EPSC005", "86000"):
        assert entidad in window, f"odonto tree missing entidad {entidad}"
    assert ", 19)" in window, "odonto tree missing the live-verbatim orden-19 branch"
    assert "P0000011" in window, "odonto tree missing shared codigo P0000011"


def test_014_reverse_rewrites_clean_by_name() -> None:
    """Reverse OR root + 5 AND branches; BEGIN/COMMIT phase3 shape is NOT used."""
    text = _text()
    window = _rule_window(text, "ide_contrato_reverse_urgencias_valido")
    assert "'OR'" in window and window.count("'AND'") == 5
    for ide in ('"986"', '"839"', '"842"', '"970"', '"974"'):
        assert ide in window, f"reverse tree missing ide_contrato {ide}"
    assert "906340" in window


def test_014_group_shapes_keep_live_fuentes() -> None:
    """Group evaluator conds keep their live group.* fuentes verbatim."""
    code = "\n".join(_code_lines(_text()))
    assert code.count("'all_values_match', 'group.collect_value_counts'") == 2
    assert "'gt', 'group.sum_cantidad'" in code
    assert "'set_intersects', 'group.collect_set_codigo'" in code
    assert "'set_contains_all', 'group.collect_set_codigo'" in code
    assert code.count('"group_by": "factura"') == 4


def test_014_seeds_no_catalogs() -> None:
    """Zero cat_in in the 6 live trees (verified) → zero catalog writes here."""
    code = "\n".join(_code_lines(_text()))
    assert "INSERT INTO catalogos" not in code
    assert "'cat_in'" not in code


def test_014_single_active_v1_per_rule() -> None:
    text = _text()
    assert "version = 2" not in text
    assert "version <> 1" not in text
    for name in EXPECTED_RULES:
        assert text.count(f"WHERE nombre = '{name}' AND version = 1") == 1


def test_014_guarded_schema_alters_like_010() -> None:
    lowered = _text().lower()
    assert "information_schema" in lowered
    assert "operador" in lowered and "valor_esperado" in lowered


def test_014_backfills_rule_base_id() -> None:
    text = _text()
    assert "rule_base_id" in text
    assert re.search(r"rule_base_id\s*=\s*id", text) is not None
    for name in ("ide_contrato_odontologia_valido", "sala_obs_check_set"):
        assert name in text
