"""TDD tests for single-flag cutover: migration 018 DDL + retired backfill.

Spec:
- 018 aligns pre-cutover retired rows (deleted before delete_rule set
  activo=false) to activo=false — engine filters ONLY by activo.
- Re-runnable: table-exists guard (008 style) + predicate matches zero
  rows on rerun. MUST NOT touch evidencias/resultados ni estado.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parent.parent.parent
    / "migrations"
    / "018_retired_rules_activo_off.sql"
)


def _read_migration() -> str:
    assert MIGRATION.exists(), "migrations/018_retired_rules_activo_off.sql must exist"
    return MIGRATION.read_text(encoding="utf-8")


def _code_only(sql: str) -> str:
    """Strip SQL line comments so assertions inspect statements, not prose."""
    return re.sub(r"--[^\n]*", "", sql)


class TestMigration018Backfill:
    def test_sets_activo_false_where_estado_retired(self):
        sql = _code_only(_read_migration())
        assert re.search(
            r"UPDATE\s+reglas\s+SET\s+activo\s*=\s*false\s+"
            r"WHERE\s+estado\s*=\s*'retired'",
            sql,
            re.IGNORECASE | re.DOTALL,
        ), "must UPDATE reglas SET activo=false WHERE estado='retired'"

    def test_rerunnable_guards(self):
        sql = _read_migration()
        assert "to_regclass" in sql, "008-style table-exists guard required"

    def test_does_not_touch_evidencias_or_resultados(self):
        sql = _code_only(_read_migration())
        assert "evidencias" not in sql.lower()
        assert "resultados_auditoria" not in sql.lower()

    def test_does_not_rewrite_estado(self):
        sql = _code_only(_read_migration())
        assert not re.search(
            r"SET\s+estado\s*=",
            sql,
            re.IGNORECASE,
        ), "018 must not rewrite estado values"
