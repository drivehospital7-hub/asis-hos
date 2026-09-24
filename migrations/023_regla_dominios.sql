-- ===========================================================================
-- 023: regla_dominios bridge table — multi-dominio scope (sdd reglas-multi-dominio)
-- ===========================================================================
-- Una regla puede aplicarse a N dominios explicitos. La tabla puente
-- regla_dominios(regla_id, dominio) es la fuente de verdad de alcance;
-- reglas.dominio queda como espejo legacy (write-through, D2) y NO se toca.
--
-- Portable PG/SQLite (sin operadores PG-only): EXISTS + INSERT..SELECT.
-- Idempotente: IF NOT EXISTS + backfill guarded. Sin BEGIN/COMMIT.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS regla_dominios (
    regla_id INTEGER NOT NULL REFERENCES reglas(id) ON DELETE CASCADE,
    dominio VARCHAR(50) NOT NULL,
    PRIMARY KEY (regla_id, dominio)
);

CREATE INDEX IF NOT EXISTS ix_regla_dominios_dominio
    ON regla_dominios (dominio, regla_id);

-- Backfill: una fila puente por cada regla existente (dominio es NOT NULL,
-- cubre el 100%). Guarded: no duplica en reruns. No modifica reglas.
INSERT INTO regla_dominios (regla_id, dominio)
SELECT id, dominio FROM reglas
WHERE NOT EXISTS (
    SELECT 1 FROM regla_dominios rd WHERE rd.regla_id = reglas.id
);
