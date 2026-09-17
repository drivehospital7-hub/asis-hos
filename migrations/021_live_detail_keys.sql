-- =============================================================================
-- 021_live_detail_keys.sql
--
-- Re-points rule-declared detalle_a/b_campo from pruned dead keys to live
-- engine problem-dict keys (frontend DETALLE_FIELD_KEYS, engine.py row copy).
-- Dead keys rendered as "" by normalized_rows._safe_format, so the old
-- values produced empty detalle cells in /procesar exports.
--
-- Mapping (exact dead value -> live value, per grupo_error family):
--   Centros de Costo  detalle_b 'centro_actual,centro_costo' -> 'centro_costo'
--   IDE Contrato      detalle_b 'ide_contrato_actual,ide_contrato' -> 'ide_contrato'
--   MAL CAPITADO      detalle_b 'ide_contrato,ide_contrato_actual' -> 'ide_contrato'
--   Tipo Usuario      detalle_b 'tipo_actual' -> 'tipo_usuario'
--   Cups Sin Contrato detalle_b 'Entidad: {codigo_entidad_cobrar}, {entidad}'
--                     -> 'Entidad: {codigo_entidad_cobrar}' (drop dead placeholder)
--   Profesionales     detalle_a 'codigo_profesional,procedimiento'
--                     -> 'codigo,procedimiento'
--                     detalle_b 'Cód: {codigo_profesional}' -> 'profesional_atiende'
--                     (degraded row path: no live key carries the professional
--                     code; the professional name is the closest live field)
--
-- Idempotent: pure UPDATEs keyed by (grupo_error, exact dead value);
-- re-running changes nothing once applied. Touches reglas only, never
-- evidencias / resultados_auditoria.
-- Run through: python run_migrations.py (version tracked in schema_migrations
-- by the runner).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Verification (read-only, run before/after; expect 0 rows after apply).
-- ---------------------------------------------------------------------------
-- SELECT nombre, grupo_error, detalle_a_campo, detalle_b_campo FROM reglas
-- WHERE detalle_a_campo = 'codigo_profesional,procedimiento'
--    OR detalle_b_campo IN ('centro_actual,centro_costo',
--                           'ide_contrato_actual,ide_contrato',
--                           'ide_contrato,ide_contrato_actual',
--                           'tipo_actual',
--                           'Cód: {codigo_profesional}',
--                           'Entidad: {codigo_entidad_cobrar}, {entidad}');

-- ---------------------------------------------------------------------------
-- 1. Centros de Costo: fallback list head was a dead key; the live tail
--    'centro_costo' already carried the value. Drop the dead head.
-- ---------------------------------------------------------------------------
UPDATE reglas SET detalle_b_campo = 'centro_costo'
WHERE grupo_error = 'Centros de Costo'
  AND detalle_b_campo = 'centro_actual,centro_costo';

-- ---------------------------------------------------------------------------
-- 2. IDE Contrato: same fallback-list shape, keep the live tail.
-- ---------------------------------------------------------------------------
UPDATE reglas SET detalle_b_campo = 'ide_contrato'
WHERE grupo_error = 'IDE Contrato'
  AND detalle_b_campo = 'ide_contrato_actual,ide_contrato';

-- ---------------------------------------------------------------------------
-- 3. MAL CAPITADO: mirrored order (live head, dead tail); keep live head.
-- ---------------------------------------------------------------------------
UPDATE reglas SET detalle_b_campo = 'ide_contrato'
WHERE grupo_error = 'MAL CAPITADO'
  AND detalle_b_campo = 'ide_contrato,ide_contrato_actual';

-- ---------------------------------------------------------------------------
-- 4. Tipo Usuario: single dead field -> live row field 'tipo_usuario'.
-- ---------------------------------------------------------------------------
UPDATE reglas SET detalle_b_campo = 'tipo_usuario'
WHERE grupo_error = 'Tipo Usuario'
  AND detalle_b_campo = 'tipo_actual';

-- ---------------------------------------------------------------------------
-- 5. Cups Sin Contrato: detalle_b template; remove the dead {entidad}
--    placeholder, keep the live {codigo_entidad_cobrar} rendering.
-- ---------------------------------------------------------------------------
UPDATE reglas SET detalle_b_campo = 'Entidad: {codigo_entidad_cobrar}'
WHERE grupo_error = 'Cups Sin Contrato'
  AND detalle_b_campo = 'Entidad: {codigo_entidad_cobrar}, {entidad}';

-- ---------------------------------------------------------------------------
-- 6. Profesionales: detalle_a pair head was dead; detalle_b template
--    referenced the group-only key, degrading to the live row path
--    'profesional_atiende' (professional name).
-- ---------------------------------------------------------------------------
UPDATE reglas
SET detalle_a_campo = 'codigo,procedimiento',
    detalle_b_campo = 'profesional_atiende'
WHERE grupo_error = 'Profesionales'
  AND detalle_a_campo = 'codigo_profesional,procedimiento'
  AND detalle_b_campo = 'Cód: {codigo_profesional}';

-- ---------------------------------------------------------------------------
-- Operator report (NOTICE only, changes no data).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    remaining integer;
BEGIN
    SELECT count(*) INTO remaining FROM reglas
    WHERE detalle_a_campo = 'codigo_profesional,procedimiento'
       OR detalle_b_campo IN ('centro_actual,centro_costo',
                              'ide_contrato_actual,ide_contrato',
                              'ide_contrato,ide_contrato_actual',
                              'tipo_actual',
                              'Cód: {codigo_profesional}',
                              'Entidad: {codigo_entidad_cobrar}, {entidad}');
    RAISE NOTICE '021: reglas still on dead detail keys: %', remaining;
END $$;

-- ---------------------------------------------------------------------------
-- Rollback (commented, best-effort: re-apply only on the exact live values
-- this migration writes, scoped by grupo_error).
-- ---------------------------------------------------------------------------
-- UPDATE reglas SET detalle_b_campo = 'centro_actual,centro_costo'
-- WHERE grupo_error = 'Centros de Costo' AND detalle_b_campo = 'centro_costo';
-- UPDATE reglas SET detalle_b_campo = 'ide_contrato_actual,ide_contrato'
-- WHERE grupo_error = 'IDE Contrato' AND detalle_b_campo = 'ide_contrato';
-- UPDATE reglas SET detalle_b_campo = 'ide_contrato,ide_contrato_actual'
-- WHERE grupo_error = 'MAL CAPITADO' AND detalle_b_campo = 'ide_contrato';
-- UPDATE reglas SET detalle_b_campo = 'tipo_actual'
-- WHERE grupo_error = 'Tipo Usuario' AND detalle_b_campo = 'tipo_usuario';
-- UPDATE reglas SET detalle_b_campo = 'Entidad: {codigo_entidad_cobrar}, {entidad}'
-- WHERE grupo_error = 'Cups Sin Contrato'
--   AND detalle_b_campo = 'Entidad: {codigo_entidad_cobrar}';
-- UPDATE reglas
-- SET detalle_a_campo = 'codigo_profesional,procedimiento',
--     detalle_b_campo = 'Cód: {codigo_profesional}'
-- WHERE grupo_error = 'Profesionales'
--   AND detalle_a_campo = 'codigo,procedimiento'
--   AND detalle_b_campo = 'profesional_atiende';
