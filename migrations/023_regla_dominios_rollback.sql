-- Rollback 023: drop the regla_dominios bridge table only.
-- reglas.dominio (legacy mirror) is untouched, so the legacy engine keeps working.
DROP TABLE IF EXISTS regla_dominios;
