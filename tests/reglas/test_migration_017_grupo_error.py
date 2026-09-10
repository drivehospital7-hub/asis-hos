"""TDD tests for dominio-grupo-error T2: migration 017 DDL + 55-rule backfill.

Spec rule-declared-grouping:
- 017 adds nullable TEXT grupo_error, detalle_a_campo, detalle_b_campo,
  descripcion_template; MUST NOT touch evidencias/resultados.
- Backfill: every seeded rule (010-016) gets non-NULL grupo_error.
- No NOT NULL constraint (deferred until cups_sin_contrato dedup).
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parent.parent.parent
    / "migrations"
    / "017_grupo_error_mapping.sql"
)
SEED_FILES = [
    "010_seed_hospitalizacion_engine_rules.sql",
    "011_seed_critical_urgencias_rules.sql",
    "012_seed_odonto_equipos_transversal.sql",
    "013_seed_rest_urgencias_hosp.sql",
    "014_seed_final_unseeded_rules.sql",
    "015_seed_intramural_gaps.sql",
    "016_seed_centro_costo_urgencias_detallado.sql",
]

NEW_COLUMNS = [
    "grupo_error",
    "detalle_a_campo",
    "detalle_b_campo",
    "descripcion_template",
]


def _read_migration() -> str:
    assert MIGRATION.exists(), "migrations/017_grupo_error_mapping.sql must exist"
    return MIGRATION.read_text(encoding="utf-8")


def _code_only(sql: str) -> str:
    """Strip SQL line comments so assertions inspect statements, not prose."""
    return re.sub(r"--[^\n]*", "", sql)


def _seeded_rule_names() -> set[str]:
    names: set[str] = set()
    migrations_dir = MIGRATION.parent
    pattern = re.compile(r"VALUES\s*\(\s*'([^']+)'")
    for seed in SEED_FILES:
        text = (migrations_dir / seed).read_text(encoding="utf-8")
        names.update(pattern.findall(text))
    return names


class TestMigration017DDL:
    def test_adds_four_nullable_text_columns(self):
        sql = _read_migration()
        for col in NEW_COLUMNS:
            assert re.search(
                rf"ADD COLUMN IF NOT EXISTS\s+{col}\s+TEXT\s+NULL",
                sql,
                re.IGNORECASE,
            ), f"missing nullable DDL for {col}"

    def test_no_not_null_on_new_columns(self):
        sql = _code_only(_read_migration())
        for col in NEW_COLUMNS:
            assert not re.search(
                rf"{col}[^;]*NOT NULL",
                sql,
                re.IGNORECASE,
            ), f"{col} must stay nullable during rollout"

    def test_does_not_touch_evidencias_or_resultados(self):
        sql = _code_only(_read_migration())
        assert "evidencias" not in sql.lower()
        assert "resultados_auditoria" not in sql.lower()

    def test_rerunnable_idempotent_markers(self):
        sql = _read_migration()
        assert sql.count("IF NOT EXISTS") >= 4


class TestMigration017Backfill:
    def test_every_seeded_rule_gets_grupo_error(self):
        sql = _read_migration()
        backfilled = set(
            re.findall(
                r"UPDATE\s+reglas\s+SET\s+grupo_error\s*=.*?WHERE\s+nombre\s*=\s*'([^']+)'",
                sql,
                re.IGNORECASE | re.DOTALL,
            )
        )
        expected = _seeded_rule_names()
        assert len(expected) == 55, f"seed inventory changed: {len(expected)}"
        missing = expected - backfilled
        assert not missing, f"rules without backfill: {sorted(missing)}"

    def test_tipo_documento_edad_maps_to_canonical_label(self):
        sql = _read_migration()
        for rule in [
            "tipo_documento_edad_menor_7",
            "tipo_documento_edad_mayor_18",
            "tipo_documento_edad_7_17",
            "tipo_documento_edad_as_menor",
            "tipo_documento_edad_ms_mayor",
            "tipo_documento_edad_cn_invalido",
            "tipo_documento_edad_ce_invalido",
        ]:
            block = re.search(
                rf"UPDATE\s+reglas\s+SET\s+grupo_error\s*=\s*'([^']+)'\s+WHERE\s+nombre\s*=\s*'{rule}'",
                sql,
                re.IGNORECASE,
            )
            assert block is not None, f"no backfill for {rule}"
            assert block.group(1) == "Tipo Identificacion / Edad"
