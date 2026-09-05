-- =============================================================================
-- Rule: sala_observacion_valido
--
-- Sala de observación: verifica que el código de sala corresponda a la
-- estancia (horas entre fec_factura y fecha_cierre) y entidad.
-- Evaluador: SalaObservacionEvaluator (sala_obs_check)
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'sala_observacion_valido',
       'Código de sala de observación incorrecto para la estancia y entidad',
       'urgencias', 'active', 1, 30, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'sala_observacion_valido' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_observacion_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- sala_obs_check evaluator: context-derived, checks invoice.codigo
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'sala_obs_check', 'invoice.codigo', '""', 0);
END $$;
