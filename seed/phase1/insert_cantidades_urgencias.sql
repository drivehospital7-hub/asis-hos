-- =============================================================================
-- Phase 1: cantidades_urgencias
-- Rule: Restricted urgency codes must have cantidad <= 1.
-- Domain: urgencias
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'cantidades_urgencias', 'Cantidad excedida (>1) para código de urgencias restringido', 'urgencias', 'active', 1, 20, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'cantidades_urgencias' AND version = 1
);

-- Clean + rebuild using DO block for reliable parent ID capture
DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'cantidades_urgencias' AND version = 1;
    IF _regla_id IS NULL THEN
        RAISE NOTICE 'Rule cantidades_urgencias not found — seed may have been skipped';
        RETURN;
    END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: AND
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'AND', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child 1: in(codigo, restricted_codes)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo',
            '["05DSB01", "5DSB01", "890601", "890701", "129B02", "12333"]', 0);

    -- Child 2: gt(cantidad, 1)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'gt', 'invoice.cantidad', '1', 1);
END $$;
