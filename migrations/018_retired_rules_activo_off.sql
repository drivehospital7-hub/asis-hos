-- =============================================================================
-- 018_retired_rules_activo_off.sql
--
-- Single-flag cutover: the engine filters ONLY by activo (no estado
-- filter). Rows retired before delete_rule switched activo off (e.g. the
-- retired+activo=true drift row) must be aligned to activo=false so a
-- stale check in the UI can never re-enable evaluation.
--
-- Re-runnable: table-exists guard (008 style) + predicate matches zero
-- rows on rerun. Does NOT touch evidencias / resultados_auditoria and
-- does NOT rewrite estado values.
-- Run through: python run_migrations.py (dry-run default, version
-- tracked in schema_migrations by the runner).
-- =============================================================================

DO $$
BEGIN
    IF to_regclass('public.reglas') IS NOT NULL THEN
        UPDATE reglas
        SET activo = false
        WHERE estado = 'retired' AND activo = true;
    ELSE
        RAISE NOTICE '018 skipped: table reglas absent';
    END IF;
END $$;
