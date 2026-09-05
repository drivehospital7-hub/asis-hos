-- =============================================================================
-- Phase 2: profesional_equipos_validos
-- Rule: Flag invoices where codigo_profesional is NOT in the valid Equipos Básicos list.
-- Domain: equipos_basicos
-- Condition: NOT(in(codigo_profesional, [valid_codes]))
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'profesional_equipos_validos', 'Profesional no válido en Equipos Básicos', 'equipos_basicos', 'active', 1, 40, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'profesional_equipos_validos' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_equipos_validos' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child: in(codigo_profesional, valid_codes)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo_profesional',
        '["03764","03762","03808","02981","03761","03766","03739","03763","02084","03825","03831","03851","03848"]', 0);
END $$;
