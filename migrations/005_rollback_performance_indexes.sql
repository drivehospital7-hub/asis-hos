-- Rollback Migration 005: Drop performance indexes
--
-- Run: psql -d asis_hos -f migrations/005_rollback_performance_indexes.sql

BEGIN;

DROP INDEX IF EXISTS ix_reglas_dominio_estado_activo_prioridad;
DROP INDEX IF EXISTS ix_condiciones_regla_id;
DROP INDEX IF EXISTS ix_excepciones_regla_id_activo;

COMMIT;
