-- Migration 004: Add rule_base_id to reglas for version grouping
-- 
-- Changes:
-- 1. ADD COLUMN rule_base_id (nullable, backfilled with id)
-- 2. DROP unique constraint on nombre (was unique=True in model)
-- 3. ADD composite unique constraint (nombre, version) for new model
--
-- Run: psql -d asis_hos -f migrations/004_add_rule_base_id.sql
-- Test: psql -d asis_hos_test -f migrations/004_add_rule_base_id.sql

BEGIN;

-- 1. Add rule_base_id column
ALTER TABLE reglas ADD COLUMN IF NOT EXISTS rule_base_id INTEGER;

-- Backfill existing rows: rule_base_id = id (each existing rule is its own base)
UPDATE reglas SET rule_base_id = id WHERE rule_base_id IS NULL;

-- 2. Drop old unique constraint on nombre
-- The constraint created by unique=True in SQLAlchemy is typically named: reglas_nombre_key
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'reglas_nombre_key' AND conrelid = 'reglas'::regclass
    ) THEN
        ALTER TABLE reglas DROP CONSTRAINT reglas_nombre_key;
    END IF;
END $$;

-- 3. Add composite unique constraint (nombre, version)
-- SQLAlchemy will create this from __table_args__, but we add it explicitly here too
-- for DB-level enforcement regardless of SQLAlchemy's auto-create behavior.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_regla_nombre_version' AND conrelid = 'reglas'::regclass
    ) THEN
        ALTER TABLE reglas ADD CONSTRAINT uq_regla_nombre_version UNIQUE (nombre, version);
    END IF;
END $$;

COMMIT;
