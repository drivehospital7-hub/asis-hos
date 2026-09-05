-- =============================================================================
-- Exception: Override threshold for PyP en ruta_duplicada
--
-- Para facturas PyP, el umbral de ruta duplicada pasa de 3 a 4.
-- Esto evita que pacientes con exactamente 3 facturas PyP y códigos
-- exemptos (990203, P0000011, 990212) sean marcados como ruta duplicada.
-- =============================================================================

INSERT INTO excepciones (regla_id, tipo_efecto, condicion_json, parametros_override, activo)
SELECT r.id, 'override', '{"convenio_facturado": "Promocion y Prevencion"}'::jsonb, '{"umbral": 4}'::jsonb, true
FROM reglas r
WHERE r.nombre = 'ruta_duplicada'
  AND r.version = 1
  AND r.activo = true
  AND NOT EXISTS (
      SELECT 1 FROM excepciones e
      WHERE e.regla_id = r.id
        AND e.condicion_json @> '{"convenio_facturado": "Promocion y Prevencion"}'::jsonb
  );
