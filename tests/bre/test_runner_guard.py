"""Runner guard tests (Slice 1, strict TDD).

Dry-run only. Never opens a prod connection. SQL-text assertions for
idempotency plus pure-function guard/dry-run/version planning checks.
"""
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")


def test_guard_aborts_on_prod_connection_name() -> None:
    from run_migrations import is_prod_database

    assert is_prod_database("control_system_prod") is True
    assert is_prod_database("ASIS_HOS_PROD") is True
    assert is_prod_database("production") is True


def test_guard_allows_dev_connection_name() -> None:
    from run_migrations import is_prod_database

    assert is_prod_database("asis_hos") is False
    assert is_prod_database("asis_hos_test") is False


def test_guard_reuses_prod_baseline_substrings() -> None:
    from run_migrations import is_prod_database
    from scripts.prod_baseline import PROD_SUBSTRINGS

    assert len(PROD_SUBSTRINGS) >= 1
    for alias in ("control_system_prod", "asis_hos_prod", "prod"):
        assert is_prod_database(alias) is True


def test_dry_run_performs_zero_writes(monkeypatch, tmp_path: Path) -> None:
    """Dry-run must plan without opening any DB connection."""
    import run_migrations

    def _forbidden_connect(*args, **kwargs):  # pragma: no cover
        raise AssertionError("dry-run must not connect")

    monkeypatch.setattr(run_migrations.psycopg2, "connect", _forbidden_connect)
    fake = tmp_path / "001_sample.sql"
    fake.write_text("SELECT 1;", encoding="utf-8")
    plan = run_migrations.plan_migrations(tmp_path, applied=set(), include_evidence=False)
    assert [p.name for p in plan] == ["001_sample.sql"]


def test_rollback_files_never_planned(tmp_path: Path) -> None:
    from run_migrations import plan_migrations

    (tmp_path / "005_add_performance_indexes.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "005_rollback_performance_indexes.sql").write_text("SELECT 1;", encoding="utf-8")
    planned = plan_migrations(tmp_path, applied=set(), include_evidence=False)
    assert [p.name for p in planned] == ["005_add_performance_indexes.sql"]

def test_double_run_reports_zero_diff(tmp_path: Path) -> None:
    from run_migrations import plan_migrations

    fake = tmp_path / "001_sample.sql"
    fake.write_text("SELECT 1;", encoding="utf-8")
    first = plan_migrations(tmp_path, applied=set(), include_evidence=False)
    second = plan_migrations(
        tmp_path, applied={p.stem for p in first}, include_evidence=False
    )
    assert first != []
    assert second == []


def test_evidence_seeds_skipped_by_default() -> None:
    from run_migrations import should_skip_evidence

    assert should_skip_evidence("011_seed_evidencias.sql", include_evidence=False) is True
    assert should_skip_evidence("012_seed_resultados_auditoria.sql", include_evidence=False) is True
    assert should_skip_evidence("010_seed_hospitalizacion_engine_rules.sql", include_evidence=False) is False
    assert should_skip_evidence("011_seed_evidencias.sql", include_evidence=True) is False


def test_idempotent_version_table_uses_if_not_exists() -> None:
    text = (MIGRATIONS_DIR / "000_schema_migrations.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "create table if not exists" in lowered
    assert "schema_migrations" in lowered


def test_idempotent_create_tables_use_if_not_exists() -> None:
    text = (MIGRATIONS_DIR / "001_create_notas_tecnicas.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "create table if not exists" in lowered
    assert "create index if not exists" in lowered


def test_idempotent_unique_constraint_is_guarded() -> None:
    text = (MIGRATIONS_DIR / "002_add_unique_constraint.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "uq_eps_contratado_cod_eps_regimen" in lowered
    assert ("if not exists" in lowered) or ("pg_constraint" in lowered)


def test_idempotent_008_has_no_bare_update() -> None:
    text = (MIGRATIONS_DIR / "008_normalize_rule_operational_states.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "retired" in lowered
    # Bare UPDATE without a table-exists guard is not rerun-safe on clones.
    assert ("information_schema" in lowered) or ("to_regclass" in lowered) or ("do $$" in lowered)


def test_idempotent_010_alter_type_is_guarded() -> None:
    text = (MIGRATIONS_DIR / "010_seed_hospitalizacion_engine_rules.sql").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "operador" in lowered
    assert ("information_schema" in lowered) or ("do $$" in lowered)
