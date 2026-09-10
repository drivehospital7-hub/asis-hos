"""TDD tests for dominio-grupo-error T3: seeds 010-016 carry grouping cols.

Spec rule-declared-grouping: seeds MUST include the 4 new columns with
ON CONFLICT (nombre, version) DO UPDATE coverage; seed labels must match
the 017 backfill labels and belong to the canonical label set.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"
MIGRATION_017 = MIGRATIONS_DIR / "017_grupo_error_mapping.sql"
SEED_FILES = [
    "010_seed_hospitalizacion_engine_rules.sql",
    "011_seed_critical_urgencias_rules.sql",
    "012_seed_odonto_equipos_transversal.sql",
    "013_seed_rest_urgencias_hosp.sql",
    "014_seed_final_unseeded_rules.sql",
    "015_seed_intramural_gaps.sql",
    "016_seed_centro_costo_urgencias_detallado.sql",
]

INSERT_PATTERN = re.compile(
    r"INSERT INTO reglas\s*\((?P<cols>[^)]+)\)\s*"
    r"VALUES\s*\((?P<vals>.*?)\)\s*"
    r"ON CONFLICT\s*\(nombre,\s*version\)\s*DO UPDATE SET\s*(?P<sets>.*?);",
    re.IGNORECASE | re.DOTALL,
)


def _iter_rule_inserts(seed: str):
    text = (MIGRATIONS_DIR / seed).read_text(encoding="utf-8")
    return list(INSERT_PATTERN.finditer(text))


def _seeded_names(seed: str) -> list[str]:
    return re.findall(
        r"INSERT INTO reglas\s*\([^)]+\)\s*VALUES\s*\(\s*'([^']+)'",
        (MIGRATIONS_DIR / seed).read_text(encoding="utf-8"),
    )


class TestSeedGroupingColumns:
    def test_each_insert_lists_four_grouping_columns(self):
        for seed in SEED_FILES:
            for match in _iter_rule_inserts(seed):
                cols = match.group("cols")
                for col in (
                    "grupo_error",
                    "detalle_a_campo",
                    "detalle_b_campo",
                    "descripcion_template",
                ):
                    assert col in cols, f"{seed}: INSERT missing {col}"

    def test_on_conflict_covers_grouping_columns(self):
        for seed in SEED_FILES:
            for match in _iter_rule_inserts(seed):
                sets = match.group("sets")
                for col in (
                    "grupo_error",
                    "detalle_a_campo",
                    "detalle_b_campo",
                    "descripcion_template",
                ):
                    assert f"{col} = EXCLUDED.{col}" in sets, (
                        f"{seed}: ON CONFLICT missing {col}"
                    )

    def test_every_seed_rule_has_non_null_grupo_error_value(self):
        for seed in SEED_FILES:
            names = _seeded_names(seed)
            assert names, f"{seed}: no rule INSERTs found"
            for match in _iter_rule_inserts(seed):
                cols = [c.strip() for c in match.group("cols").split(",")]
                assert "grupo_error" in cols, f"{seed}: INSERT missing grupo_error"
                name_m = re.match(r"\s*'([^']+)'", match.group("vals"))
                rule = name_m.group(1) if name_m else "?"
                gi = cols.index("grupo_error")
                strvals = re.findall(r"'((?:[^']|'{2})*)'|(\b\d+\b|true|false|NULL)", match.group("vals"))
                flat = [a.replace("''", "'") if b == "" else None if b == "NULL" else b for a, b in strvals]
                assert flat[gi], f"{seed}:{rule} grupo_error VALUE is NULL"


class TestSeedBackfillAgreement:
    def test_seed_labels_match_017_backfill(self):
        from app.constants.grupo_error import ALL_GRUPO_ERROR_LABELS

        migration = MIGRATION_017.read_text(encoding="utf-8")
        backfill = {
            rule: label
            for label, rule in re.findall(
                r"SET\s+grupo_error\s*=\s*'([^']+)'\s+WHERE\s+nombre\s*=\s*'([^']+)'",
                migration,
            )
        }
        for seed in SEED_FILES:
            for match in _iter_rule_inserts(seed):
                cols = [c.strip() for c in match.group("cols").split(",")]
                name_m = re.match(r"\s*'([^']+)'", match.group("vals"))
                assert name_m is not None
                rule = name_m.group(1)
                assert "grupo_error" in cols, f"{seed}:{rule} INSERT missing grupo_error"
                # grupo_error is the first appended value: locate by position
                gi = cols.index("grupo_error")
                strvals = re.findall(r"'((?:[^']|'{2})*)'|(\b\d+\b|true|false|NULL)", match.group("vals"))
                flat = [a.replace("''", "'") if b == "" else None if b == "NULL" else b for a, b in strvals]
                label = flat[gi]
                assert label in ALL_GRUPO_ERROR_LABELS, (
                    f"{seed}:{rule} unknown label {label!r}"
                )
                assert backfill.get(rule) == label, (
                    f"{seed}:{rule} seed label {label!r} != 017 backfill {backfill.get(rule)!r}"
                )
