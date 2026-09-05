-- Migration 000: schema_migrations version table.
--
-- Tracks applied migration versions for idempotent reruns.
-- Rerun-safe: CREATE TABLE IF NOT EXISTS + additive-only DDL.
-- Run through: python run_migrations.py (dry-run default)

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
