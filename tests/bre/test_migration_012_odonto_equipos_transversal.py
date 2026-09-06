"""Migration 012 tests (strict TDD, SQL-text only — zero DB writes).

012 seeds the odontología + equipos_basicos + transversal engine rules +
catalogs by (nombre, version), idempotent DELETE+INSERT pattern like 010/011.
Never hardcodes live row IDs.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "012_seed_odonto_equipos_transversal.sql"

EXPECTED_RULES = {
    # odontologia (4)
    "centro_costo_odontologia_valido": "odontologia",
    "profesional_odontologia_valido": "odontologia",
    "ruta_duplicada": "odontologia",
    "valores_decimales": "odontologia",
    # equipos_basicos (2)
    "centro_costo_equipos_basicos_valido": "equipos_basicos",
    "profesional_equipos_validos": "equipos_basicos",
    # transversal (16)
    "cantidad_consultas_anomalas": "transversal",
    "cantidad_general_anomalas": "transversal",
    "cantidad_pyp_anomalas": "transversal",
    "codigo_entidad": "transversal",
    "cups_sin_contrato": "transversal",
    "doble_tipo_procedimiento": "transversal",
    "entidad_86000_requiere_as_ms": "transversal",
    "tipo_documento_edad_7_17": "transversal",
    "tipo_documento_edad_as_menor": "transversal",
    "tipo_documento_edad_ce_invalido": "transversal",
    "tipo_documento_edad_cn_invalido": "transversal",
    "tipo_documento_edad_mayor_18": "transversal",
    "tipo_documento_edad_menor_7": "transversal",
    "tipo_documento_edad_ms_mayor": "transversal",
    "tipo_id_requiere_entidad_86000": "transversal",
    "tipo_usuario_valido": "transversal",
}

EXPECTED_CATALOGS = (
    "codigos_exceptuados",
    "centro_costo_pyp",
    "centro_costo_quirofano",
    "centro_costo_hospitalizacion",
    "centros_costo_laboratorio_validos",
    "centros_costo_pyp_intramural",
    "centros_costo_validos_intramural",
    "profesionales_odontologia",
    "profesionales_equipos_basicos",
    "tipo_usuario_validos",
    "entidades_ess",
    "codigos_exceptuados_ambulatorio",
    "codigos_exceptuados_responsable_urgencias",
    "codigos_excluidos_vacunacion",
    "codigos_tipo_procedimiento_ambulatorio",
    "codigos_tipo_procedimiento_laboratorio",
)

# Catalog keys referenced via operador='cat_in' by the seeded trees.
EXPECTED_CAT_IN_KEYS = (
    "profesionales_odontologia",
    "profesionales_equipos_basicos",
    "tipo_usuario_validos",
    "codigos_exceptuados",
    "centro_costo_pyp",
    "centro_costo_quirofano",
    "centro_costo_hospitalizacion",
)


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """SQL lines with full-line comments stripped (cat_in audit ignores comments)."""
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


def test_012_file_exists() -> None:
    assert MIGRATION.exists(), "012 migration file missing"


def test_012_planned_after_011() -> None:
    from run_migrations import plan_migrations

    planned = [p.stem for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)]
    assert "011_seed_critical_urgencias_rules" in planned
    assert "012_seed_odonto_equipos_transversal" in planned
    assert planned.index("011_seed_critical_urgencias_rules") < planned.index(
        "012_seed_odonto_equipos_transversal"
    )


def test_012_not_treated_as_evidence_seed() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
    assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False


def test_012_upserts_each_rule_by_name_version() -> None:
    text = _text()
    for name, dominio in EXPECTED_RULES.items():
        pattern = re.compile(
            r"'%s',\s*'.*?',\s*'%s',\s*'active',\s*1," % (re.escape(name), re.escape(dominio)),
            re.DOTALL,
        )
        assert pattern.search(text), f"rule {name} not upserted as ('name', {dominio}, active, v1)"
    assert text.count("ON CONFLICT (nombre, version) DO UPDATE") >= len(EXPECTED_RULES)


def test_012_rebuilds_conditions_by_name() -> None:
    text = _text()
    for name in EXPECTED_RULES:
        if name in ("centro_costo_odontologia_valido", "centro_costo_equipos_basicos_valido"):
            # F14 loop resolves these two via a _rule_names array variable.
            assert re.search(r"'%s'" % re.escape(name), text), (
                f"rule {name} missing from F14 _rule_names array"
            )
            continue
        assert re.search(
            r"WHERE nombre = '%s' AND version = 1" % re.escape(name), text
        ), f"rule {name} conditions not resolved by (nombre, version)"
    # Generic by-name lookup used by the F14 loop + per-rule DO blocks.
    assert "WHERE nombre = _rule_name AND version = 1" in text
    assert text.count("DELETE FROM condiciones WHERE regla_id = ") >= len(EXPECTED_RULES) - 1


def test_012_no_hardcoded_rule_ids() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"regla_id\s*=\s*\d+", code) is None, "hardcoded regla_id literal found"
    assert re.search(r"padre_id\s*=\s*\d+", code) is None, "hardcoded padre_id literal found"


def test_012_no_transaction_control() -> None:
    code = "\n".join(_code_lines(_text()))
    assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
    assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None


def test_012_seeds_expected_catalogs_additively() -> None:
    lowered = _text().lower()
    for key in EXPECTED_CATALOGS:
        assert key in lowered, f"catalog {key} missing"
    assert lowered.count("where not exists (select 1 from catalogos where key =") >= len(
        EXPECTED_CATALOGS
    )


def test_012_seeded_trees_use_expected_cat_in_keys() -> None:
    """Seeded centro_costo/profesional/tipo_usuario trees resolve via cat_in."""
    code = "\n".join(_code_lines(_text()))
    assert "'cat_in'" in code, "012 seeds no cat_in conditions — catalog keys would dangle"
    for key in EXPECTED_CAT_IN_KEYS:
        assert re.search(
            r"'cat_in',\s*'invoice\.[a-z_]+',\s*(to_jsonb\('%s'::text\)|'\"%s\"')"
            % (re.escape(key), re.escape(key)),
            code,
        ), f"cat_in key {key} not referenced by any seeded tree"


def test_012_excludes_noted_rules() -> None:
    text = _text()
    code = "\n".join(_code_lines(text))
    # Excluded rules may be named in header comments, never in executable code.
    for excluded in (
        "ide_contrato_odontologia_valido",
        "detect_duplicados_base",
        "ide_contrato_equipos_basicos_valido",
    ):
        assert excluded not in code, f"excluded rule {excluded} seeded in executable code"
        assert excluded in text, f"excluded rule {excluded} not documented in header"
    assert "Excluded" in text
    assert "version = 2" not in text
    assert "version <> 1" not in text


def test_012_guarded_schema_alters_like_010() -> None:
    lowered = _text().lower()
    assert "information_schema" in lowered
    assert "operador" in lowered and "valor_esperado" in lowered


def test_012_centro_costo_uses_f14_full_tree() -> None:
    """Odonto/equipos centro_costo seed the F14 OR tree (cat_in), not phase4 inline."""
    text = _text()
    for name in ("centro_costo_odontologia_valido", "centro_costo_equipos_basicos_valido"):
        idx = text.find("'%s'" % name)
        assert idx != -1
    code = "\n".join(_code_lines(text))
    assert "centro_costo_pyp" in code
    assert "centro_costo_quirofano" in code
    assert "centro_costo_hospitalizacion" in code
    assert "codigos_exceptuados" in code


def test_012_backfills_rule_base_id() -> None:
    text = _text()
    assert "rule_base_id" in text
    assert re.search(r"rule_base_id\s*=\s*id", text) is not None
    for name in ("ruta_duplicada", "tipo_usuario_valido", "doble_tipo_procedimiento"):
        assert name in text
