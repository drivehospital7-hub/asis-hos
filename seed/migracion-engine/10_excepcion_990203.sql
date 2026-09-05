-- =============================================================================
-- Exception: Código 990203 skip doble_tipo_procedimiento
--
-- Permite que facturas con código 990203 tengan múltiples tipos de procedimiento
-- sin ser marcadas como error. El engine saltará las filas con codigo=990203
-- al evaluar la regla doble_tipo_procedimiento.
-- =============================================================================

INSERT INTO excepciones (regla_id, tipo_efecto, condicion_json, activo)
SELECT r.id, 'skip', '{"codigo": "990203"}'::jsonb, true
FROM reglas r
WHERE r.nombre = 'doble_tipo_procedimiento'
  AND r.version = 1
  AND r.activo = true
  AND NOT EXISTS (
      SELECT 1 FROM excepciones e
      WHERE e.regla_id = r.id
        AND e.condicion_json @> '{"codigo": "990203"}'::jsonb
  );
