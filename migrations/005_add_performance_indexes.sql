-- Migration 005: Add composite performance indexes for rule engine
--
-- Context: The BRMS rule engine queries reglas, condiciones, and excepciones
-- tables multiple times per domain evaluation. These composite indexes eliminate
-- sequential scans for the most common query patterns.
--
-- Changes:
-- 1. Composite index on reglas(dominio, estado, activo, prioridad) for RuleResolver
-- 2. Index on condiciones(regla_id) for condition loading per rule
-- 3. Composite index on excepciones(regla_id, activo) for exception queries per rule
--
-- Run: psql -d asis_hos -f migrations/005_add_performance_indexes.sql
-- Test: psql -d asis_hos_test -f migrations/005_add_performance_indexes.sql
-- Rollback: migrations/005_rollback_performance_indexes.sql

BEGIN;

-- 1. Composite index for RuleResolver queries:
--    SELECT * FROM reglas WHERE dominio = :domain AND estado = 'active'
--    AND activo = true ORDER BY prioridad ASC
CREATE INDEX IF NOT EXISTS ix_reglas_dominio_estado_activo_prioridad
    ON reglas (dominio, estado, activo, prioridad);

-- 2. Index for condition loading:
--    SELECT * FROM condiciones WHERE regla_id = :id ORDER BY padre_id ASC, orden ASC
CREATE INDEX IF NOT EXISTS ix_condiciones_regla_id
    ON condiciones (regla_id);

-- 3. Composite index for exception queries:
--    SELECT * FROM excepciones WHERE regla_id = :id AND activo = true
CREATE INDEX IF NOT EXISTS ix_excepciones_regla_id_activo
    ON excepciones (regla_id, activo);

COMMIT;
