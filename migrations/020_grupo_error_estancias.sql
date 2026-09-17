-- =============================================================================
-- 020_grupo_error_estancias.sql
--
-- Crea el grupo_error 'Estancias' (plain group: mapper generico de
-- normalized_rows, sin formatter con nombre) y mueve la regla 74
-- (urg_sala_obs_menor_2_horas) + hermanas de estancia (72/70/73/67).
--
-- Criterio (confirmado contra prod por estructura, no por id en vivo):
--   1. nombre = 'urg_sala_obs_menor_2_horas' (regla 74), o
--   2. detalle_a/b_campo = 'estancia_str' con grupo_error Cantidades* (o sin
--      grupo), o descripcion_template con '{estancia_str}', o
--   3. grupo_error Cantidades* en dominio urgencias con fuente date.horas /
--      estancia_horas en su arbol de condiciones.
--
-- EXCLUSION: la regla 61 (Cups-Equivalentes con estancia_str) NO se mueve:
-- los UPDATEs por criterio excluyen id = 61 y grupo 'Cups-Equivalentes'.
--
-- Idempotente: UPDATEs puros por (nombre, version) y por criterio estable;
-- re-correr no cambia nada una vez aplicado. Solo toca reglas, nunca
-- evidencias / resultados_auditoria.
-- Run through: python run_migrations.py (version tracked in schema_migrations
-- by the runner).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Regla 74 por nombre (vive en prod; si no existe en dev/test no hace nada).
-- ---------------------------------------------------------------------------
UPDATE reglas SET grupo_error = 'Estancias'
WHERE nombre = 'urg_sala_obs_menor_2_horas' AND version = 1;

-- ---------------------------------------------------------------------------
-- 2. Hermanas con detalle estancia declarado en grupo Cantidades* (o sin grupo).
--    Excluye la 61 y todo Cups-Equivalentes.
-- ---------------------------------------------------------------------------
UPDATE reglas SET grupo_error = 'Estancias'
WHERE version = 1
  AND id <> 61
  AND COALESCE(grupo_error, '') <> 'Cups-Equivalentes'
  AND (
        detalle_a_campo = 'estancia_str'
     OR detalle_b_campo = 'estancia_str'
     OR descripcion_template LIKE '%{estancia_str}%'
  )
  AND (
        grupo_error LIKE 'Cantidades%'
     OR grupo_error IS NULL
     OR grupo_error = ''
  );

-- ---------------------------------------------------------------------------
-- 3. Hermanas sin detalle declarado: Cantidades de urgencias cuyo arbol
--    referencia horas de estancia (date.horas / estancia_horas).
--    Excluye la 61 y todo Cups-Equivalentes.
-- ---------------------------------------------------------------------------
UPDATE reglas SET grupo_error = 'Estancias'
WHERE version = 1
  AND id <> 61
  AND dominio = 'urgencias'
  AND grupo_error LIKE 'Cantidades%'
  AND COALESCE(grupo_error, '') <> 'Cups-Equivalentes'
  AND EXISTS (
        SELECT 1 FROM condiciones c
        WHERE c.regla_id = reglas.id
          AND c.fuente_datos LIKE '%horas%'
  );

-- ---------------------------------------------------------------------------
-- Reporte operador (solo NOTICE, no cambia datos).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    moved integer;
BEGIN
    SELECT count(*) INTO moved FROM reglas
    WHERE grupo_error = 'Estancias' AND version = 1;
    RAISE NOTICE '020: reglas en grupo Estancias: %', moved;
END $$;
