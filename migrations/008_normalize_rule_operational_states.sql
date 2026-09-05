-- Rule CRUD now operates only on active and retired states.
-- Hardened Slice 1: table-exists guard via to_regclass; the UPDATE itself
-- is rerun-stable (second run matches zero rows). Paired with
-- RULE_STATES = {"active", "retired"} in app/constants/base.py.
-- Run through: python run_migrations.py (dry-run default)

DO $$
BEGIN
    IF to_regclass('public.reglas') IS NOT NULL THEN
        UPDATE reglas
        SET estado = 'retired'
        WHERE estado IN ('draft', 'deprecated');
    ELSE
        RAISE NOTICE '008 skipped: table reglas absent';
    END IF;
END $$;
