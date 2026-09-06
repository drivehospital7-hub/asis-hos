"""Migration 011 tests (strict TDD, SQL-text only — zero DB writes).

011 seeds the CRITICAL urgencias engine rules + catalogs by (nombre, version),
idempotent DELETE+INSERT pattern like 010. Never hardcodes live row IDs.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "011_seed_critical_urgencias_rules.sql"

EXPECTED_RULES = (
    "cups_equivalentes",
    "ide_contrato_urgencias_valido",
    "mal_capitado",
    "centro_costo_urgencias_valido",
    "copago_entidad_valido",
    "cantidades_urgencias",
    "cantidades_soat_urgencias",
    "revision_entidad_86",
)

EXPECTED_CATALOGS = (
    "centros_costo_validos_urgencias",
    "profesionales_urgencias",
    "facturadores_urgencias",
    "codigos_exceptuados_responsable_urgencias",
)


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """SQL lines with full-line comments stripped (cat_in audit ignores comments)."""
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def test_011_file_exists() -> None:
    assert MIGRATION.exists(), "011 migration file missing"


def test_011_planned_after_010() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "010_seed_hospitalizacion_engine_rules" in planned
    assert "011_seed_critical_urgencias_rules" in planned
    assert planned.index("010_seed_hospitalizacion_engine_rules") < planned.index(
        "011_seed_critical_urgencias_rules"
    )


def test_011_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False


def test_011_upserts_each_rule_by_name_version() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'urgencias',\s*'active',\s*1," % re.escape(name), re.DOTALL
        )
        assert pattern.search(text), f"rule {name} not upserted as ('name', urgencias, active, v1)"
    assert text.count("ON CONFLICT (nombre, version) DO UPDATE") >= len(EXPECTED_RULES)


def test_011_rebuilds_conditions_by_name() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        assert re.search(
            r"WHERE nombre = '%s' AND version = 1" % re.escape(name), text
        ), f"rule {name} conditions not resolved by (nombre, version)"
    assert text.count("DELETE FROM condiciones WHERE regla_id = ") >= len(EXPECTED_RULES)


def test_011_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None, "hardcoded regla_id literal found"
    assert re.search(r"padre_id\s*=\s*\d+", code) is None, "hardcoded padre_id literal found"


def test_011_no_transaction_control() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None


def test_011_seeds_expected_catalogs_additively() -> None:
    lowered = _text().lower()
    for key in EXPECTED_CATALOGS:
        assert key in lowered, f"catalog {key} missing"
    assert lowered.count("where not exists (select 1 from catalogos where key =") >= len(
        EXPECTED_CATALOGS
    )


def test_011_seeded_conditions_use_no_cat_in() -> None:
    """Seeded trees use inline sets; catalogs serve sibling rules (documented in header)."""
    code = "\n".join(_code_lines(_text()))
    assert "'cat_in'" not in code, "011 seeds its own cat_in conditions — catalog keys would dangle"
    header = _text()
    for consumer in ("profesional_urgencias_valido", "centro_costo_intramural_valido"):
        assert consumer in header, f"sibling consumer {consumer} not documented"


def test_011_excludes_reverse_and_retired_history() -> None:
    text = _text()
    code = "\n".join(_code_lines(text))
    # Excluded rule may be named in header comments, never in executable code.
    assert "ide_contrato_reverse_urgencias_valido" not in code
    assert "Excluded" in text and "ide_contrato_reverse_urgencias_valido" in text
    assert "version = 2" not in text
    assert "version <> 1" not in text


def test_011_guarded_schema_alters_like_010() -> None:
    lowered = _text().lower()
    assert "information_schema" in lowered
    assert "operador" in lowered and "valor_esperado" in lowered


def test_011_centro_costo_reactivates_v1() -> None:
    """dev holds 8 RETIRED centro_costo versions, zero active: v1 upsert must flip active."""
    text = _text()
    idx = text.find("'centro_costo_urgencias_valido'")
    assert idx != -1
    window = text[idx : idx + 2000]
    assert "estado = 'active'" in window
    assert "activo = true" in window


def test_011_backfills_rule_base_id() -> None:
    text = _text()
    assert "rule_base_id" in text
    assert re.search(r"rule_base_id\s*=\s*id", text) is not None
