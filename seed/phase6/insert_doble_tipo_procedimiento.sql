-- =============================================================================
-- Phase 6: doble_tipo_procedimiento
-- Rule: Flag invoices with more than one distinct tipo_procedimiento.
-- Domain: transversal
-- Evaluation: group-by → distinct_count aggregation
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo, parametros)
SELECT 'doble_tipo_procedimiento',
       'Factura con más de un tipo de procedimiento',
       'transversal', 'active', 1, 35, 'error', true,
       '[{"group_by": "numero_factura", "aggregations": [{"function": "distinct_count", "field": "tipo_procedimiento", "target": "distinct_count_tipo_procedimiento"}]}]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'doble_tipo_procedimiento' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'doble_tipo_procedimiento' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: gt(invoice.distinct_count_tipo_procedimiento, 1)
    -- More than 1 distinct tipo_procedimiento → MATCH
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'atomic', 'gt', 'invoice.distinct_count_tipo_procedimiento', '1', 0);
END $$;
