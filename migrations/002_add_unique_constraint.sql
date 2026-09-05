-- Agregar constraint unique compuesto a eps_contratado
-- Unique: (cod_contrato, eps, regimen)
-- Hardened Slice 1: guarded by pg_constraint check; rerun-safe.
-- Run through: python run_migrations.py (dry-run default)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_eps_contratado_cod_eps_regimen'
          AND conrelid = 'eps_contratado'::regclass
    ) THEN
        ALTER TABLE eps_contratado
        ADD CONSTRAINT uq_eps_contratado_cod_eps_regimen UNIQUE (cod_contrato, eps, regimen);
    END IF;
END $$;
