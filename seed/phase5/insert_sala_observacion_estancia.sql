-- =============================================================================
-- Phase 5: sala_observacion_estancia_prolongada
-- Rule: Flag Urgencias invoices where estancia exceeds 6 hours.
-- Domain: urgencias
-- Uses date.horas (computed from fec_factura and fecha_cierre).
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'sala_observacion_estancia_prolongada',
       'Estancia en Urgencias superior a 6 horas — requiere código de sala de observación',
       'urgencias', 'active', 1, 32, 'warning', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'sala_observacion_estancia_prolongada' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'sala_observacion_estancia_prolongada' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: AND
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child 1: gt(date.horas, 6)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gt', 'date.horas', '6', 0);

    -- Child 2: eq(tipo_factura_descripcion, "Urgencias")
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'eq', 'invoice.tipo_factura_descripcion', '"Urgencias"', 1);
END $$;
