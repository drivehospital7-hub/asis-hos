-- =============================================================================
-- Phase 2: profesional_urgencias_valido
-- Rule: Flag invoices where codigo_profesional is NOT in the valid Urgencias list.
-- Domain: urgencias
-- Condition: NOT(in(codigo_profesional, [valid_codes]))
-- =============================================================================

INSERT INTO reglas (nombre, descripcion, dominio, estado, version, prioridad, severidad, activo)
SELECT 'profesional_urgencias_valido', 'Profesional no válido en Urgencias', 'urgencias', 'active', 1, 40, 'error', true
WHERE NOT EXISTS (
    SELECT 1 FROM reglas WHERE nombre = 'profesional_urgencias_valido' AND version = 1
);

DO $$
DECLARE
    _regla_id INT;
    _root_id INT;
BEGIN
    SELECT id INTO _regla_id FROM reglas WHERE nombre = 'profesional_urgencias_valido' AND version = 1;
    IF _regla_id IS NULL THEN RETURN; END IF;

    DELETE FROM condiciones WHERE regla_id = _regla_id;

    -- Root: NOT
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, NULL, 'composite', 'NOT', NULL, NULL, 0)
    RETURNING id INTO _root_id;

    -- Child: in(codigo_profesional, valid_codes)
    INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
    VALUES (_regla_id, _root_id, 'atomic', 'in', 'invoice.codigo_profesional',
        '["03568","01235","01960","03493","03822","01293","02249","03799","03222","03384","03154","01289","03628","03893","03710","01868","03742","03857","03365","03730","02217","03374","03255"]', 0);
END $$;
