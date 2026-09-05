"""Hardened PostgreSQL migration runner.

Prod-guarded, dry-run by default, version-tracked via schema_migrations.
Never connects when the connection name matches prod. Additive SQL only.
"""

import argparse
import logging
import os
from pathlib import Path

import psycopg2

from app.utils.db_config import get_database_config
from scripts.prod_baseline import PROD_SUBSTRINGS

logger = logging.getLogger(__name__)

EVIDENCE_MARKERS = ("evidencia", "auditoria")


def is_prod_database(name: str) -> bool:
    """Return True when a connection name matches a prod alias."""
    lowered = (name or "").lower()
    matched = any(token in lowered for token in PROD_SUBSTRINGS)
    if matched:
        logger.error("[BACK][ERROR] Refusing prod connection: %s", name)
    return matched


def should_skip_evidence(filename: str, include_evidence: bool) -> bool:
    """Return True when an evidence/audit seed must be skipped."""
    if include_evidence:
        return False
    lowered = (filename or "").lower()
    skipped = any(marker in lowered for marker in EVIDENCE_MARKERS)
    if skipped:
        logger.info("[BACK] Skipping evidence seed: %s", filename)
    return skipped


def _include_evidence_from_env() -> bool:
    """SKIP_EVIDENCE_AUDIT=1 (default) skips evidence seeds."""
    return os.getenv("SKIP_EVIDENCE_AUDIT", "1") == "0"


def plan_migrations(
    migrations_dir: Path | str,
    applied: set[str] | frozenset[str] | None = None,
    include_evidence: bool = False,
) -> list[Path]:
    """Plan ordered pending migrations without touching the database."""
    applied_versions = set(applied or set())
    directory = Path(migrations_dir)
    if not directory.exists():
        logger.warning("[BACK] Missing migrations directory: %s", directory)
        return []
    planned: list[Path] = []
    for sql_file in sorted(directory.glob("*.sql")):
        if "rollback" in sql_file.stem.lower():
            logger.info("[BACK] Skipping rollback file: %s", sql_file.name)
            continue
        if sql_file.stem in applied_versions:
            continue
        if should_skip_evidence(sql_file.name, include_evidence):
            continue
        planned.append(sql_file)
    logger.info("[BACK] Planned %d migration(s)", len(planned))
    return planned


def get_applied_versions(cursor) -> set[str]:
    """Return applied versions, empty when the version table is absent."""
    try:
        cursor.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cursor.fetchall()}
    except psycopg2.Error:
        logger.info("[BACK] Version table absent, planning all files")
        return set()


def record_version(cursor, version: str) -> None:
    """Record one applied version idempotently."""
    cursor.execute(
        "INSERT INTO schema_migrations (version) VALUES (%s) "
        "ON CONFLICT (version) DO NOTHING",
        (version,),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse runner flags; dry-run is the default mode."""
    parser = argparse.ArgumentParser(description="Hardened migration runner")
    parser.add_argument("--apply", action="store_true", help="Apply migrations")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, zero writes (default)")
    parser.add_argument("--confirm", action="store_true", help="Manual confirm gate")
    parser.add_argument("--with-evidence", action="store_true", help="Backfill evidence seeds")
    parser.add_argument("--migrations-dir", default="migrations", help="Migrations directory")
    return parser.parse_args(argv)


def _abort(message: str) -> int:
    logger.error("[BACK][ERROR] %s", message)
    print(f"Abortado: {message}")
    return 1


def _dry_run_report(config_name: str, planned: list[Path], skipped: int) -> int:
    logger.info("[BACK] Dry-run on %s: %d planned, %d skipped", config_name, len(planned), skipped)
    print(f"Dry-run [{config_name}]: {len(planned)} planned, {skipped} skipped, 0 writes")
    for sql_file in planned:
        print(f"  plan: {sql_file.name}")
    return 0


def _apply_files(cursor, planned: list[Path]) -> tuple[int, list[str]]:
    ok_count = 0
    errors: list[str] = []
    for sql_file in planned:
        logger.info("[BACK] Applying migration: %s", sql_file.name)
        try:
            sql_content = sql_file.read_text(encoding="utf-8")
            cursor.execute(sql_content)
            record_version(cursor, sql_file.stem)
            ok_count += 1
        except psycopg2.Error as exc:
            logger.error("[BACK][ERROR] Migration failed %s: %s", sql_file.name, exc)
            errors.append(sql_file.name)
    return ok_count, errors


def run_migrations(argv: list[str] | None = None) -> int:
    """Execute migrations; dry-run default, --apply --confirm to write."""
    args = parse_args(argv)
    config = get_database_config()
    if is_prod_database(config.name):
        return _abort(f"refusing prod database '{config.name}'")
    migrations_dir = Path(args.migrations_dir)
    include_evidence = bool(args.with_evidence) or _include_evidence_from_env()
    if not args.apply:
        planned = plan_migrations(migrations_dir, set(), include_evidence)
        all_files = sorted(migrations_dir.glob("*.sql")) if migrations_dir.exists() else []
        skipped = len(all_files) - len(planned)
        return _dry_run_report(config.name, planned, skipped)
    if not args.confirm:
        return _abort("apply requires explicit --confirm")
    conn = psycopg2.connect(**config.psycopg2_dsn)
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        applied = get_applied_versions(cursor)
        planned = plan_migrations(migrations_dir, applied, include_evidence)
        ok_count, errors = _apply_files(cursor, planned)
        cursor.close()
    finally:
        conn.close()
    logger.info("[BACK] Migrations applied: %d ok, %d errors", ok_count, len(errors))
    print(f"Aplicadas: {ok_count} ok, {len(errors)} errores")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(run_migrations())
